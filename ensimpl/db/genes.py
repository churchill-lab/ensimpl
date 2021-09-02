import sqlite3
from collections import OrderedDict
from typing import Dict
from typing import List
from typing import Optional

from ensimpl.db import dbs
from ensimpl.db import meta
from ensimpl import utils

LOG = utils.get_logger()

EXTERNAL_DBS = [
    'Ensembl',
    'EntrezGene',
    'Uniprot_gn',
    'MGI',
    'HGNC',
]


SQL_GENES_ALL = '''
SELECT g.ensembl_id match_id,
       g.ensembl_id ensembl_id, 
       g.ensembl_id gene_id,
       g.ensembl_version gene_version,
       g.species_id gene_species_id,
       g.symbol gene_symbol,
       g.name gene_name,
       g.synonyms gene_synonyms,
       g.external_ids gene_external_ids,
       g.chromosome gene_chromosome,
       g.start_position gene_start,
       g.end_position gene_end,
       g.strand gene_strand,
       g.homolog_ids homolog_ids,
       'EG' type_key
  FROM ensembl_genes g
'''

SQL_GENES_FILTERED = '''
SELECT t.ensembl_id match_id,
       g.ensembl_id ensembl_id, 
       g.ensembl_id gene_id,
       g.ensembl_version gene_version,
       g.species_id gene_species_id,
       g.symbol gene_symbol,
       g.name gene_name,
       g.synonyms gene_synonyms,
       g.external_ids gene_external_ids,
       g.chromosome gene_chromosome,
       g.start_position gene_start,
       g.end_position gene_end,
       g.strand gene_strand,
       g.homolog_ids homolog_ids,
       'EG' type_key
  FROM ensembl_genes g,
       (SELECT eg.gene_id, eg.ensembl_id 
          FROM ensembl_gtpe eg
         WHERE eg.ensembl_id in (SELECT ensembl_id 
                                   FROM {})) t       
 WHERE g.ensembl_id = t.gene_id
'''

SQL_GENES_FULL_ALL = '''
SELECT g.ensembl_id match_id,
       g.ensembl_id gene_id,
       g.ensembl_version gene_version,
       g.species_id gene_species_id,
       g.symbol gene_symbol,
       g.name gene_name,
       g.synonyms gene_synonyms,
       g.external_ids gene_external_ids,
       g.chromosome gene_chromosome,
       g.start_position gene_start,
       g.end_position gene_end,
       g.strand gene_strand,
       g.homolog_ids homolog_ids,
       r.*
  FROM ensembl_genes g,
       ensembl_gtpe r
 WHERE g.ensembl_id = r.gene_id
'''

SQL_GENES_FULL_FILTERED = '''
SELECT t.ensembl_id match_id,
       g.ensembl_id gene_id,
       g.ensembl_version gene_version,
       g.species_id gene_species_id,
       g.symbol gene_symbol,
       g.name gene_name,
       g.synonyms gene_synonyms,
       g.external_ids gene_external_ids,
       g.chromosome gene_chromosome,
       g.start_position gene_start,
       g.end_position gene_end,
       g.strand gene_strand,
       g.homolog_ids homolog_ids,
       r.*
  FROM ensembl_genes g,
       ensembl_gtpe r,       
       (SELECT eg.gene_id, eg.ensembl_id 
          FROM ensembl_gtpe eg
         WHERE eg.ensembl_id in (SELECT ensembl_id 
                                   FROM {})) t       
 WHERE g.ensembl_id = r.gene_id
   AND r.gene_id = t.gene_id  
'''


SQL_GENES_ORDER_BY_ID = ' ORDER BY g.ensembl_id'

SQL_GENES_ORDER_BY_POSITION = '''
 ORDER BY cast(
       replace(replace(replace(g.chromosome,'X','50'),'Y','51'),'MT','51') 
       AS int), g.start_position, g.end_position
'''

SQL_HOMOLOGY = '''
SELECT eh.ensembl_id,
       eh.ensembl_version,
       eh.ensembl_symbol,
       eh.perc_id query_id_perc,
       eh.homolog_id,
       eh.homolog_version,
       eh.homolog_symbol,
       eh.homolog_perc_id target_id_perc,
       eh.dn,
       eh.ds,
       eh.goc_score,
       eh.wga_coverage,
       eh.is_high_confidence conf
  FROM ensembl_homologs eh 
 ORDER BY eh.ensembl_id, eh.homolog_id
'''

SQL_HOMOLOGY_FILTERED = '''
SELECT eh.ensembl_id,
       eh.ensembl_version,
       eh.ensembl_symbol,
       eh.perc_id query_id_perc,
       eh.homolog_id,
       eh.homolog_version,
       eh.homolog_symbol,
       eh.homolog_perc_id target_id_perc,
       eh.dn,
       eh.ds,
       eh.goc_score,
       eh.wga_coverage,
       eh.is_high_confidence conf
  FROM ensembl_homologs eh
 WHERE eh.ensembl_id in ({})
 ORDER BY eh.ensembl_id, eh.homolog_id
'''

SQL_IDS_FILTERED = '''
SELECT all_ids.ensembl_id,
       all_ids.external_id,
       all_ids.external_db,
       matches.match_id
  FROM (SELECT ensembl_id, external_id, external_db
          FROM ensembl_gene_ids        
         UNION        
        SELECT ensembl_id, homolog_id external_id, 'Ensembl_homolog' external_db
          FROM ensembl_homologs
       ) all_ids,
       (SELECT distinct ensembl_id, external_id match_id
          FROM ensembl_gene_ids
         WHERE external_id in ({})
           AND external_db = "{}"
       ) matches
 WHERE matches.ensembl_id = all_ids.ensembl_id       
 ORDER BY all_ids.ensembl_id, all_ids.external_db, all_ids.external_id
'''

SQL_IDS_FILTERED_ENSEMBL = '''
SELECT all_ids.ensembl_id,
       all_ids.external_id,
       all_ids.external_db,
       matches.match_id
  FROM (SELECT ensembl_id, external_id, external_db
          FROM ensembl_gene_ids        
         UNION        
        SELECT ensembl_id, homolog_id external_id, 'Ensembl_homolog' external_db
          FROM ensembl_homologs
       ) all_ids,
       (SELECT distinct ensembl_id, ensembl_id match_id
          FROM ensembl_gene_ids
         WHERE ensembl_id in ({})
       ) matches
 WHERE matches.ensembl_id = all_ids.ensembl_id       
 ORDER BY all_ids.ensembl_id, all_ids.external_db, all_ids.external_id
'''

SQL_IDS_ALL = '''
SELECT all_ids.ensembl_id,
       all_ids.external_id,
       all_ids.external_db,
       matches.match_id
  FROM (SELECT ensembl_id, external_id, external_db
          FROM ensembl_gene_ids        
         UNION        
        SELECT ensembl_id, homolog_id external_id, 'Ensembl_homolog' external_db
          FROM ensembl_homologs
       ) all_ids,
       (SELECT distinct ensembl_id, ensembl_id match_id
          FROM ensembl_gene_ids
       ) matches
 WHERE matches.ensembl_id = all_ids.ensembl_id       
 ORDER BY all_ids.ensembl_id, all_ids.external_db, all_ids.external_id
'''

SQL_IDS_RANDOM = '''
SELECT r.*
  FROM (SELECT external_id random_id, external_db source_db
          FROM ensembl_gene_ids 
         UNION
        SELECT ensembl_id, 'Ensembl' 
          FROM ensembl_genes 
        ) r
WHERE r.source_db = :source_db       
ORDER BY RANDOM() 
LIMIT :limit
'''

SQL_EXON_INFO = '''
    SELECT gtpe.* 
      FROM ensembl_genes g,
           ensembl_gtpe gtpe,
           chromosomes c
     WHERE g.ensembl_id = gtpe.gene_id 
       AND gtpe.seqid = c.chromosome
       AND gtpe.type_key not in ('ET', 'EP')
'''

SQL_EXON_INFO_ORDER_BY = '''
     ORDER BY c.chromosome_num, 
           g.start_position, 
           gtpe.gene_id, 
           ifnull(gtpe.exon_number, 0)
'''


def get_ids(db: str, ids: Optional[List[str]] = None,
            source_db: Optional[str] = 'Ensembl') -> Dict:
    """Get all ids for identifiers.

    Args:
        db: The Ensimpl database.
        ids: A list of Ensembl identifiers.
        source_db: A valid source_db.

    Returns:
        A dict of identifiers.

    Raises:
        Exception: When sqlite error or other error occurs.
    """
    results = OrderedDict()

    valid_db_ids = ['Ensembl', 'Ensembl_homolog']

    external_dbs = meta.external_dbs(db)

    for ext_db in external_dbs:
        valid_db_ids.append(ext_db['external_db_id'])

    if source_db not in valid_db_ids:
        raise ValueError(f'Valid source dbs are: {",".join(valid_db_ids)}')

    try:
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        #
        # build the query
        #

        sql_query = SQL_IDS_ALL

        if ids:
            in_values = '","'.join(ids)
            in_values = f'"{in_values}"'

            if source_db and source_db.lower() == 'ensembl':
                sql_query = SQL_IDS_FILTERED_ENSEMBL
                sql_query = sql_query.format(in_values)
            else:
                sql_query = SQL_IDS_FILTERED
                sql_query = sql_query.format(in_values, source_db)

        #
        # execute the query
        #

        for row in cursor.execute(sql_query, {}):

            match_id = row['match_id']

            match = results.get(match_id,
                                {'Ensembl': [row['ensembl_id']]})

            id_arr = match.get(row['external_db'], [])
            id_arr.append(row['external_id'])

            match[row['external_db']] = id_arr

            results[match_id] = match

        cursor.close()
        conn.close()

    except sqlite3.Error as e:
        raise Exception(e)

    return results


def get_homology(db: str, ids: Optional[List[str]] = None) -> Dict:
    """Get homology information.

    Args:
        db: The Ensimpl database.
        ids: A list of Ensembl identifiers.

    Returns:
        A dict of homology information.

    Raises:
        Exception: When sqlite error or other error occurs.
    """
    results = OrderedDict()

    try:
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        #
        # build the query
        #

        sql_query = SQL_HOMOLOGY

        if ids:
            sql_query = SQL_HOMOLOGY_FILTERED

            in_values = '","'.join(ids)
            in_values = f'"{in_values}"'

            # create a temp table and insert into
            sql_query = sql_query.format(in_values)

        #
        # execute the query
        #

        for row in cursor.execute(sql_query, {}):
            gene_id = row['ensembl_id']

            gene = results.get(gene_id)

            if not gene:
                gene = []

            gene.append(utils.dictify_row(cursor, row))

            results[gene_id] = gene

        cursor.close()
        conn.close()

    except sqlite3.Error as e:
        raise Exception(e)

    return results


def get(db: str, ids: Optional[List[str]] = None, order: Optional[str] = 'id',
        details: Optional[bool] = False) -> Dict:
    """
    Get genes matching the ids.

    Args:
        db: The Ensimpl database.
        ids: A list of Ensembl identifiers.
        order: Order by 'id' or 'position'.
        details: True to retrieve all information including transcripts,
            exons, proteins.  False will only retrieve the top level gene
            information.

    Returns:
        A list of dicts representing genes.

        Each match object will contain:

        =================  =======  ============================================
        Element            Type     Description
        =================  =======  ============================================
        ensembl_id         string   Ensembl gene identifier
        ensembl_version    integer  version of the identifier
        species_id         string   species identifier: 'Mm', 'Hs', etc
        chromosome         string   the chromosome
        start              integer  start position in base pairs
        end                integer  end position in base pairs
        strand             string   '+' or '-'
        gene_name          string   name of the gene
        gene_symbol        string   gene symbol
        gene_synonyms      list     list of strings
        gene_external_ids  list     each having keys of 'db' and 'db_id'
        homolog_ids        list     each having keys of 'homolog_id' and
                                    'homolog_symbol'
        =================  =======  ============================================

        If ``full`` is ``True``, each match will also contain the following:

        ``transcripts``, with each item containing:

        =================  =======  ============================================
        Element            Type     Description
        =================  =======  ============================================
        id                 string   Ensembl gene identifier
        ensembl_version    integer  version of the identifier
        symbol             string   transcript symbol
        start              integer  start position in base pairs
        end                integer  end position in base pairs
        exons              list     dict of: number,id,start,end,ensembl_version
        protein            dict     id, start, end, ensembl_version
        =================  =======  ============================================


    Raises:
        Exception: When sqlite error or other error occurs.
    """
    results = OrderedDict()

    try:
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        #
        # build the query
        #

        sql_query = None

        if ids:
            if details:
                sql_query = SQL_GENES_FULL_FILTERED
            else:
                sql_query = SQL_GENES_FILTERED

            # create a temp table and insert into
            temp_table = f'lookup_ids_{utils.create_random_string()}'

            sql_temp = (f'CREATE TEMPORARY TABLE {temp_table} ( '
                        'ensembl_id TEXT, '
                        'PRIMARY KEY (ensembl_id) );')

            cursor.execute(sql_temp)

            sql_temp = f'INSERT INTO {temp_table} VALUES (?);'
            _ids = [(_,) for _ in ids]
            cursor.executemany(sql_temp, _ids)

            # make sure we add the temp table name to the query
            sql_query = sql_query.format(temp_table)
        else:
            if details:
                sql_query = SQL_GENES_FULL_ALL
            else:
                sql_query = SQL_GENES_ALL

        if order and order.lower() == 'position':
            sql_query = f'{sql_query} {SQL_GENES_ORDER_BY_POSITION}'
        else:
            sql_query = f'{sql_query} {SQL_GENES_ORDER_BY_ID}'


        #
        # execute the query
        #

        for row in cursor.execute(sql_query, {}):
            gene_id = row['gene_id']
            ensembl_id = row['ensembl_id']
            match_id = row['match_id']

            gene = results.get(match_id)

            if not gene:
                gene = {'id': gene_id, 'transcripts': {}}

            if row['type_key'] == 'EG':
                gene['species_id'] = row['gene_species_id']
                gene['chromosome'] = row['gene_chromosome']
                gene['start'] = row['gene_start']
                gene['end'] = row['gene_end']
                gene['strand'] = '+' if row['gene_strand'] > 0 else '-'

                if row['gene_version']:
                    gene['ensembl_version'] = row['gene_version']

                if row['gene_symbol']:
                    gene['symbol'] = row['gene_symbol']

                if row['gene_name']:
                    gene['name'] = row['gene_name']

                if row['gene_synonyms']:
                    row_synonyms = row['gene_synonyms']
                    gene['synonyms'] = row_synonyms.split('||')

                if row['gene_external_ids']:
                    row_external_ids = row['gene_external_ids']
                    external_ids = []
                    if row_external_ids:
                        tmp_external_ids = row_external_ids.split('||')
                        for e in tmp_external_ids:
                            elem = e.split('/')
                            external_ids.append({'db': elem[0], 'db_id': elem[1]})
                    gene['external_ids'] = external_ids

                if row['homolog_ids']:
                    row_homolog_ids = row['homolog_ids']
                    homolog_ids = []
                    if row_homolog_ids:
                        tmp_homolog_ids = row_homolog_ids.split('||')
                        for e in tmp_homolog_ids:
                            elem = e.split('/')
                            homolog_ids.append({'id': elem[0],
                                                'symbol': elem[1]})
                    gene['homolog_ids'] = homolog_ids

            elif row['type_key'] == 'ET':
                transcript_id = row['transcript_id']
                transcript = {'id': transcript_id, 'exons': {}}

                if row['ensembl_id_version']:
                    transcript['version'] = row['ensembl_id_version']

                if row['ensembl_symbol']:
                    transcript['symbol'] = row['ensembl_symbol']

                transcript['start'] = row['start']
                transcript['end'] = row['end']

                gene['transcripts'][transcript_id] = transcript

            elif row['type_key'] == 'EE':
                transcript_id = row['transcript_id']
                transcript = gene['transcripts'].get(transcript_id,
                                                     {'id': transcript_id,
                                                      'exons': {}})

                exon = {'id': ensembl_id,
                        'start': row['start'],
                        'end': row['end'],
                        'number': row['exon_number']}

                if row['ensembl_id_version']:
                    exon['version'] = row['ensembl_id_version']

                transcript['exons'][ensembl_id] = exon

                gene['transcripts'][transcript_id] = transcript

            elif row['type_key'] == 'EP':
                transcript_id = row['transcript_id']
                transcript = gene['transcripts'].get(transcript_id,
                                                     {'id': transcript_id,
                                                      'exons': {}})

                transcript['protein'] = {'id': ensembl_id,
                                         'start': row['start'],
                                         'end': row['end']}

                if row['ensembl_id_version']:
                    transcript['protein']['version'] = row['ensembl_id_version']

                gene['transcripts'][transcript_id] = transcript
            else:
                LOG.error('Unknown')

            results[match_id] = gene

        cursor.close()

        if details:
            homologs = get_homology(db, ids)

            # convert transcripts, etc to sorted list rather than dict
            ret = OrderedDict()
            for (gene_id, gene) in results.items():
                if gene:
                    t = []
                    for (transcript_id, transcript) in gene['transcripts'].items():
                        e = []
                        for (exon_id, exon) in transcript['exons'].items():
                            e.append(exon)
                        transcript['exons'] = sorted(e, key=lambda ex: ex['number'])
                        t.append(transcript)
                    gene['transcripts'] = sorted(t, key=lambda tr: tr['start'])

                gene['homologs'] = homologs.get(gene_id, None)

                ret[gene_id] = gene
            results = ret
        else:
            ret = OrderedDict()
            for (gene_id, gene) in results.items():
                if gene:
                    del gene['transcripts']
                ret[gene_id] = gene

            results = ret

        cursor.close()
        conn.close()

    except sqlite3.Error as e:
        raise Exception(e)

    return results


def random_ids(db: str, source_db: Optional[str] = 'Ensembl',
               limit: Optional[int] = 10):
    """Get random ids.

    Args:
        db: The Ensimpl database.
        source_db: source database identifier
        limit: Number of ids to return

    Returns:
        A list of Ensembl IDs (str)

    """
    valid_db_ids = ['Ensembl', 'Ensembl_homolog']
    external_dbs = meta.external_dbs(db)

    for ext_db in external_dbs:
        valid_db_ids.append(ext_db['external_db_id'])

    if source_db not in valid_db_ids:
        raise ValueError(f'Valid source dbs are: {",".join(valid_db_ids)}')

    sql_statement = SQL_IDS_RANDOM

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    params = {'source_db': source_db,
              'limit': int(limit)}

    ids = []

    for row in cursor.execute(sql_statement, params):
        ids.append(row['random_id'])

    cursor.close()
    conn.close()

    return ids


def get_history(databases: List[str], ensembl_id: str,
                details: Optional[bool] = False):
    """Get a genes history.

    Args:
        databases: The Ensimpl databases.
        ensembl_id: The Ensembl identifier.
        details: True to retrieve all information including transcripts,
            exons, proteins.  False will only retrieve the top level gene
            information. Not yet implemented.

    Returns:
        list: A dictionary of database details.

    Raises:
        Exception: When sqlite error or other error occurs.
    """
    results = {}

    try:
        for database in databases:
            rs = dbs.get_release_species(database)
            results[rs['release']] = get(database, [ensembl_id], details)

    except ValueError as e:
        LOG.debug(e)

    return results


def compute_union(exon_starts: List[int], exon_ends: List[int]) -> List:
    edges = [(x, 1) for x in exon_starts] + [(x, -1) for x in exon_ends]
    edges.sort(key=lambda pos: pos[0])

    intervals = []
    height = 0
    start = 0

    for t in edges:
        if height == 0:
            start = t[0]

        height += t[1]
        if height == 0:
            intervals.append((start, t[0]))

    return intervals


def run_length_encode(reference: int, intervals: List[int]) -> List[int]:
    """
    Returns alternating exon and gap lengths.
    """
    deltas = []

    for t in intervals:
        delta = t[0] - reference
        deltas.append(delta)
        reference = reference + delta

        delta = t[1] - reference
        deltas.append(delta)
        reference = reference + delta

    return deltas


def split_exons(exon_string: str) -> List[int]:
    return [int(x) for x in exon_string.split(',') if x != '']


def get_exon_info(db: str, chrom: Optional[str] = None,
                  compress: Optional[bool] = False) -> List:
    """Get homology information.

    Args:
        db: The Ensimpl database.
        chrom: Chromosome specific, None for all
        compress: compress dict to list

    Returns:
        list: A ``list`` of ``dicts`` representing gene data and exons.

    Raises:
        Exception: When sqlite error or other error occurs.
    """
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if chrom is not None:
        sql_where = f' AND gtpe.seqid = "{chrom}" '
    else:
        sql_where = ''

    sql_query = f'{SQL_EXON_INFO} {sql_where} {SQL_EXON_INFO_ORDER_BY}'

    genes = {}

    for row in cursor.execute(sql_query, {}):

        tx_start = int(row['start'])
        tx_end = int(row['end'])

        if row['type_key'] == 'EG':

            ensembl_id = row['ensembl_id']

            genes[ensembl_id] = {
                'id': ensembl_id,
                'symbol': row['ensembl_symbol'],
                'chr': row['seqid'],
                'txStart': tx_start,
                'txEnd': tx_end,
                'strand': row['strand'],
                'exonStarts': [],
                'exonEnds': [],
            }
        else:
            gene = genes[ensembl_id]

            gene['exonStarts'].append(tx_start)
            gene['exonEnds'].append(tx_end)

    cursor.close()
    conn.close()

    ret = []

    if compress:
        for gene in genes.values():
            exons = ','.join([str(x) for x in run_length_encode(
                gene['txStart'],
                compute_union(gene['exonStarts'], gene['exonEnds']))])

            ret.append([
                gene['id'],
                gene['symbol'],
                gene['chr'],
                gene['txStart'],
                gene['txEnd'] - gene['txStart'],
                gene['strand'],
                exons
            ])
    else:
        for gene in genes.values():
            exons = [x for x in run_length_encode(
                gene['txStart'],
                compute_union(gene['exonStarts'], gene['exonEnds']))]

            ret.append({
                'id': gene['id'],
                'symbol': gene['symbol'],
                'chr': gene['chr'],
                'start': gene['txStart'],
                'length': gene['txEnd'] - gene['txStart'],
                'strand': gene['strand'],
                'exons': exons
            })

    return ret


