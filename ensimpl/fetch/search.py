# -*- coding: utf_8 -*-
import sqlite3
import re

import ensimpl.utils as utils
import ensimpl.fetch.utils as fetch_utils

LOG = utils.get_logger()

REGEX_ENSEMBL_MOUSE_ID = re.compile('ENSMUS([EGTP])[0-9]{11}', re.IGNORECASE)
REGEX_ENSEMBL_HUMAN_ID = re.compile('ENS([EGTP])[0-9]{11}', re.IGNORECASE)
REGEX_MGI_ID = re.compile('MGI:[0-9]{1,}', re.IGNORECASE)
REGEX_REGION = re.compile('(CHR|)*\s*([0-9]{1,2}|X|Y|MT)\s*(-|:)?\s*(\d+)\s*(MB|M|K|)?\s*(-|:|)?\s*(\d+|)\s*(MB|M|K|)?', re.IGNORECASE)

SQL_TERM_EXACT = '''
SELECT MAX(s.score||'||'||s.description||'||'||l.lookup_value) AS match_description, 
       s.score, l.ensembl_gene_id, g.*
  FROM ensembl_genes g,
       ensembl_genes_lookup l,
       search_ranking s
WHERE g.ensembl_id = l.ensembl_gene_id
  AND l.ranking_id = s.ranking_id
  AND l.lookup_value = :term
GROUP BY l.ensembl_gene_id
ORDER BY match_description - length(match_description) DESC, g.symbol ASC
'''

SQL_TERM_LIKE = '''
SELECT MAX(s.score||'||'||s.description||'||'||l.lookup_value) AS match_description, 
       s.score, l.ensembl_gene_id, g.*
  FROM ensembl_genes g,
       ensembl_genes_lookup l,
       ensembl_search es,
       search_ranking s
WHERE g.ensembl_id = l.ensembl_gene_id
  AND l.ranking_id = s.ranking_id
  AND es.ensembl_genes_lookup_key = l.ensembl_genes_lookup_key
  AND es.lookup_value MATCH :term
GROUP BY l.ensembl_gene_id
ORDER BY match_description - length(match_description) DESC, g.symbol ASC
'''

SQL_ID = '''
SELECT MAX(s.score||'||'||s.description||'||'||l.lookup_value) AS match_description, 
       s.score, l.ensembl_gene_id, g.*
  FROM ensembl_genes g,
       ensembl_genes_lookup l,
       ensembl_search es,
       search_ranking s
WHERE g.ensembl_id = l.ensembl_gene_id
  AND l.ranking_id = s.ranking_id
  AND es.ensembl_genes_lookup_key = l.ensembl_genes_lookup_key
  AND l.ranking_id in ('EG', 'ET', 'EE', 'EP', 'ZG', 'MI', 'UG', 'HG')
  AND es.lookup_value MATCH :term
GROUP BY l.ensembl_gene_id
ORDER BY match_description - length(match_description) DESC, g.symbol ASC
'''

SQL_REGION = '''
SELECT *
  FROM ensembl_genes e
 WHERE e.chromosome = :chromosome
   AND e.start_position <= :end_position
   AND e.end_position >= :start_position
 ORDER BY cast(
       replace(replace(replace(e.chromosome,'X','50'),'Y','51'),'MT','51') 
       AS int), e.start_position, e.end_position
'''

QUERIES = {}
QUERIES['SQL_TERM_EXACT'] = SQL_TERM_EXACT
QUERIES['SQL_TERM_LIKE'] = SQL_TERM_LIKE
QUERIES['SQL_ID'] = SQL_ID
QUERIES['SQL_REGION'] = SQL_REGION


class SearchException(Exception):
    """Search exception class."""
    pass


class Query:
    """Encapsulate query objects.
    """
    def __init__(self, term=None, exact=False):
        """Initialization.

        Args:
            term (str, optional): The search term.
            exact (bool, optional): ``True`` for exact match of `term`.
        """
        self.term = term
        self.exact = exact
        self.region = None
        self.query = None

    def __str__(self):
        """Return a string representation of this query"""
        return (f'Query Object: term="{self.term}", "region="{self.region}",'
                f' exact="{self.exact}", query="{self.query}"')

    def get_parameters(self):
        """Get the query parameters.

        Returns:
            dict: if region, than keys are 'chromosome', 'start_position',
                'end_position'. Otherwise, the key is 'term'
        """
        if self.region:
            return {'chromosome': self.region.chromosome,
                    'start_position': self.region.start_position,
                    'end_position': self.region.end_position}
        return {'term': self.term}


class Match:
    """Represent a match object.
    """
    def __init__(self, ensembl_gene_id=None, ensembl_version=None,
                 external_ids=None, symbol=None, name=None, synonyms=None,
                 species=None, chromosome=None, position_start=None,
                 position_end=None, strand=None, homolog_ids=None,
                 match_reason=None, match_value=None, score=None):
        """Constructor.

        Args:
            ensembl_gene_id (str, optional): Ensembl gene identifier.
            ensembl_version (int, optional): Ensembl gene version
            external_ids (list, optional): holds ``dict`` of external ids
            symbol (str, optional): Ensembl gene symbol.
            name (str, optional): Ensembl gene name.
            synonyms (list, optional): each element is a synonym (``str``)
            species (str, optional): Species identifier.
            chromosome (str, optional): Ensembl gene chromosome.
            position_start (int, optional): start location on `chromosome`
            position_end (int, optional): end location on `chromosome`
            strand (str, optional): ``+`` or ``-``
            homolog_ids (str, optional): homolog gene ids
            match_reason (str, optional): The key the term matched on.
            match_value (str, optional): The value the term matched on.
            score (int, optional): Match score
        """
        #: str: Ensembl gene identifier
        self.ensembl_gene_id = ensembl_gene_id

        #: str: Ensembl gene version
        self.ensembl_version = ensembl_version
        self.external_ids = external_ids
        self.species = species
        self.symbol = symbol
        self.name = name
        self.synonyms = synonyms
        self.chromosome = chromosome
        self.position_start = position_start
        self.position_end = position_end
        self.strand = strand
        self.homolog_ids = homolog_ids
        self.match_reason = match_reason
        self.match_value = match_value
        self.score = score

    def __str__(self):
        return str(self.ensembl_gene_id)

    def dict(self):
        """For JSON representation.

        Returns:
            dict: With keys representing all the attributes.
        """
        return self.__dict__


class Result:
    """Simple class to encapsulate a Query and matches
    """
    def __init__(self, query=None, matches=None, num_results=None):
        """Constructor.

        Args:
            query (Query, optional): The ``Query`` object.
            matches (list, optional): ``list`` of ``Match`` objects.
            num_results (int, optional): The maximum number of matches.
        """
        self.query = query
        self.matches = matches
        self.num_matches = len(matches) if matches else 0
        self.num_results = num_results


def get_query(term, exact=True):
    """Get query based upon parameters

    Args:
        term (str): The search term.
        exact (bool, optional): ``True`` for exact match of `term`.

    Returns:
        Query: The query.

    Raises:
        ValueError: When `term` is invalid.
    """
    if not term:
        raise ValueError('No term')

    valid_term = term.strip()

    if len(valid_term) <= 0:
        raise ValueError('Empty term')

    query = Query(term, exact)

    if REGEX_ENSEMBL_MOUSE_ID.match(valid_term):
        query.query = QUERIES['SQL_ID']
    elif REGEX_ENSEMBL_HUMAN_ID.match(valid_term):
        query.query = QUERIES['SQL_ID']
    elif REGEX_MGI_ID.match(valid_term):
        query.query = QUERIES['SQL_ID']
    elif REGEX_REGION.match(valid_term) and fetch_utils.is_valid_region(term):
        query.query = QUERIES['SQL_REGION']
        query.region = fetch_utils.str_to_region(term)
    else:
        if exact:
            query.query = QUERIES['SQL_TERM_EXACT']
        else:
            query.query = QUERIES['SQL_TERM_LIKE']

            if valid_term[-1] != '*':
                valid_term = valid_term + '*'

            query.term = valid_term

    return query


def execute_query(query, release=None, species=None, limit=None):
    """Execute the SQL query.

    Args:
        query (:obj:`Query`): the query
        release (str): The Ensembl release or ``None`` for latest.
        species (str): The Ensembl species identifier.
        limit (int, optional): Maximum number to return, ``None`` for all.

    Returns:
        :obj:`Result`: The resulting object.

    Raises:
        SearchException: When a sqlite error or other error occur.
    """
    if not query:
        raise ValueError('No query')

    matches = []
    ilimit = fetch_utils.nvli(limit, -1)

    try:
        conn = fetch_utils.connect_to_database(release, species)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        gene_id = 'ensembl_gene_id'
        if query.region:
            gene_id = 'ensembl_id'

        for row in cursor.execute(query.query, query.get_parameters()):
            match = Match()

            match.ensembl_gene_id = row[gene_id]
            match.ensembl_version = row['ensembl_version']
            match.species = row['species_id']
            match.symbol = row['symbol']
            match.name = row['name']

            row_external_ids = row['external_ids']
            external_ids = []
            if row_external_ids:
                tmp_external_ids = row_external_ids.split('||')
                for e in tmp_external_ids:
                    elem = e.split('/')
                    external_ids.append({'db': elem[0], 'db_id': elem[1]})
            match.external_ids = external_ids

            row_homolog_ids = row['homolog_ids']
            homolog_ids = []
            if row_homolog_ids:
                tmp_homolog_ids = row_homolog_ids.split('||')
                for h in tmp_homolog_ids:
                    elem = h.split('/')
                    homolog_ids.append({'homolog_id': elem[0],
                                        'homolog_symbol': elem[1]})
            match.homolog_ids = homolog_ids

            row_synonyms = row['synonyms']
            synonyms = []
            if row_synonyms:
                synonyms = row_synonyms.split('||')

            match.synonyms = synonyms
            match.chromosome = row['chromosome']
            match.position_start = row['start_position']
            match.position_end = row['end_position']
            match.strand = '+' if row['strand'] > 0 else '-'

            if query.region:
                match.match_reason = 'Region'
                match.match_value = '{}:{}-{}'.format(str(match.chromosome),
                                                      str(match.position_start),
                                                      str(match.position_end))
            else:
                row_match_description = row['match_description']
                if row_match_description:
                    desc = row_match_description.split('||')
                match.match_reason = desc[1]
                match.match_value = desc[2]
                match.score = row['score'] - len(row_match_description)

            matches.append(match)

        cursor.close()
        conn.close()
    except sqlite3.Error as e:
        LOG.error('Database Error: {}'.format(e))
        raise SearchException(e)
    except Exception as e:
        LOG.error('Search Error: {}'.format(e))
        raise SearchException(e)

    num_matches = len(matches)

    if limit and len(matches) > ilimit:
        matches = matches[:ilimit]

    return Result(query, matches, num_matches)


def search(term, release=None, species=None, exact=True, limit=None):
    """Perform the search.

    Args:
        term (str): The search term.
        release (str): The Ensembl release.
        species (str): The Ensembl species identifier.
        exact (bool, optional): ``True`` for exact match of `term`.
        limit (int, optional): Maximum number to return, ``None`` for all.

    Returns:
        :obj:`Result`: The result of the query.
    """
    LOG.debug('term={}'.format(term))
    LOG.debug('release={}'.format(release))
    LOG.debug('species={}'.format(species))
    LOG.debug('exact={}'.format(exact))
    LOG.debug('limit={}'.format(limit))

    try:
        query = get_query(term, exact)

        LOG.debug('QUERY={}'.format(query))

        result = execute_query(query, release, species, limit)

        LOG.debug('# matches: {}'.format(len(result.matches)))

        return result
    except SearchException as se:
        LOG.error('Error: {}'.format(se))
        return None

