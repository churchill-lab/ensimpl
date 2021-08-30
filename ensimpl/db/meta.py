# -*- coding: utf_8 -*-
from collections import OrderedDict
import sqlite3

from ensimpl import utils
from ensimpl.db import dbs

LOG = utils.get_logger()


def chromosomes(db):
    """Get the chromosomes.

    Args:
        db (str): The Ensimpl database.

    Returns:
        list: A ``list`` of ``dicts`` with the following keys:
            * chromosome
            * length
            * order

    """
    sql_statement = 'SELECT * FROM chromosomes ORDER BY chromosome_num '

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    chroms = []

    for row in cursor.execute(sql_statement):
        chroms.append({
            'chromosome': row['chromosome'],
            'length': row['chromosome_length'],
            'order': row['chromosome_num']
        })

    cursor.close()
    conn.close()

    return chroms


def karyotypes(db):
    """Get the karyotypes.

    Args:
        db (str): The Ensimpl database.

    Returns:
        list: A ``list`` element with a ``dict`` with the following keys:
            * chromosome
            * length
            * order
            * karyotypes
                * seq_region_start
                * seq_region_end
                * band
                * stain
    """
    sql_statement = '''
        SELECT * 
          FROM karyotypes k, chromosomes c
         WHERE k.chromosome = c.chromosome
        ORDER BY c.chromosome_num, k.seq_region_start
    '''

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    karyotype_data = OrderedDict()

    for row in cursor.execute(sql_statement):
        chrom_data = karyotype_data.get(row['chromosome'],
                                        {'chromosome': row['chromosome'],
                                         'length': row['chromosome_length'],
                                         'order': row['chromosome_num'],
                                         'karyotypes': []})

        chrom_data['karyotypes'].append(
            {'seq_region_start': row['seq_region_start'],
             'seq_region_end': row['seq_region_end'],
             'band': row['band'],
             'stain': row['stain']}
        )

        karyotype_data[row['chromosome']] = chrom_data

    cursor.close()
    conn.close()

    # turn into a list
    return list(karyotype_data.values())

def db_meta(db):
    """Get the database meta information..

    Args:
        db (str): The Ensimpl database.

    Returns:
        dict: A ``dict`` with the following keys:
            * assembly
            * assembly_patch
            * species
            * release
            * url (if available)
    """
    sql_meta = '''
        SELECT distinct meta_key meta_key, meta_value, species_id
          FROM meta_info
         ORDER BY meta_key
    '''
    meta_data = {}

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    for row in cursor.execute(sql_meta):
        meta_data['species'] = row['species_id']

        for val in ['release', 'assembly', 'assembly_patch', 'url']:
            if row['meta_key'] == val:
                meta_data[val] = row['meta_value']

    cursor.close()
    conn.close()

    return meta_data

def stats(db):
    """Get information for the version.

    Args:
        db (str): The Ensimpl database.

    Returns:
        dict: A ``dict`` with the following keys:
            * assembly
            * assembly_patch
            * species
            * stats - informational counts about the database
            * version
    """
    sql_lookup_stats = '''
        SELECT count(egl.lookup_value) num, sr.description 
          FROM ensembl_genes_lookup egl, search_ranking sr
         WHERE egl.ranking_id = sr.ranking_id
         GROUP BY sr.description, egl.species_id 
         ORDER BY sr.score desc
    '''

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    stats = {}

    for row in cursor.execute(sql_lookup_stats):
        stats[row['description']] = row['num']

    cursor.close()
    conn.close()

    return stats


def external_dbs(db):
    """Get the external databases.

    Args:
        db (str): The Ensimpl database.

    Returns:
        list: A ``list`` of ``dicts`` with the following keys:
            * external_db_id
            * external_db_name
            * ranking_id

    """
    sql_statement = 'SELECT * FROM external_dbs ORDER BY external_db_key '

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    ext_dbs = []

    rs = dbs.get_release_species(db)

    species_id = rs['species']

    for row in cursor.execute(sql_statement):
        if species_id.lower() == 'hs' and row['ranking_id'] == 'MI':
            continue
        elif species_id.lower() == 'mm' and row['ranking_id'] == 'HG':
            continue

        ext_dbs.append({
            'external_db_id': row['external_db_id'],
            'external_db_name': row['external_db_name'],
            'ranking_id': row['ranking_id']
        })

    cursor.close()
    conn.close()

    return ext_dbs
