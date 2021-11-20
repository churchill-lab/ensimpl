import os
import re
import sqlite3

from typing import List
from typing import Optional

import ensimpl.utils as utils

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

QUERIES = {
    'SQL_TERM_EXACT':  SQL_TERM_EXACT,
    'SQL_TERM_LIKE': SQL_TERM_LIKE,
    'SQL_ID': SQL_ID,
    'SQL_REGION': SQL_REGION
}


class SearchException(Exception):
    """Search exception class."""
    pass


class Query:
    """Encapsulate query objects.
    """
    def __init__(self, term: Optional[str] = None,
                 exact: Optional[bool] = False):
        """Initialization.

        Args:
            term: The search term.
            exact: True for exact match of `term`.
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
    def __init__(self,
                 query: Optional[Query] = None,
                 matches: Optional[List[Match]] = None,
                 num_results: Optional[int] = None):
        """Constructor.

        Args:
            query: The Query object.
            matches: A list of Matches.
            num_results: The maximum number of matches.
        """
        self.query = query
        self.matches = matches
        self.num_matches = len(matches) if matches else 0
        self.num_results = num_results


def get_query(term: str, exact: Optional[bool] = True) -> Query:
    """Get query based upon parameters

    Args:
        term: The search term.
        exact: True for exact match.

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
    elif REGEX_REGION.match(valid_term) and utils.is_valid_region(term):
        query.query = QUERIES['SQL_REGION']
        query.region = utils.str_to_region(term)
    else:
        if exact:
            query.query = QUERIES['SQL_TERM_EXACT']
        else:
            query.query = QUERIES['SQL_TERM_LIKE']

            if valid_term[-1] != '*':
                valid_term = valid_term + '*'

            query.term = valid_term

    return query


def execute_query(db: str, query: Query, limit: Optional[int] = None) -> Result:
    """Execute the SQL query.

    Args:
        db (str): The Ensembl database.
        query (:obj:`Query`): the query
        limit (int, optional): Maximum number to return, ``None`` for all.

    Returns:
        :obj:`Result`: The resulting object.

    Raises:
        SearchException: When a sqlite error or other error occur.
    """
    if not query:
        raise ValueError('No query')

    matches = []
    ilimit = utils.nvli(limit, -1)

    try:
        # prevent erroneously creating a database
        if not os.path.isfile(db):
            raise FileNotFoundError(db)

        conn = sqlite3.connect(db)
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


def search(db: str, term: str,
           exact: Optional[bool] = True,
           limit: Optional[int] = None) -> Optional[Result]:
    """Perform the search.

    Args:
        db: The Ensembl database.
        term: The search term.
        exact: True for exact match of `term`.
        limit: Maximum number to return, None for all.

    Returns:
        The result of the query.
    """
    try:
        query = get_query(term, exact)
        result = execute_query(db, query, limit)

        return result
    except SearchException as se:
        LOG.error('Error: {}'.format(se))
        return None

