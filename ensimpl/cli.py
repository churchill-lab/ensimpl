# -*- coding: utf-8 -*-
from enum import Enum
import os
import sys
import time
from pathlib import Path

import json

import typer

from typing import List, Optional

from tabulate import tabulate

import ensimpl.create.create_ensimpl as create_ensimpl
from ensimpl.db import dbs
from ensimpl.db import genes as genesdb
from ensimpl.db import meta
from ensimpl.db import search as searchdb
from ensimpl.utils import configure_logging, format_time, get_logger

app = typer.Typer()

ensimpl_dbs = None
ensimpl_dbs_dict = None


@app.command()
def create(directory: Path = typer.Option(
               None, '--directory', '-d', 
               help='defaults to current directory'),
           release: Optional[List[str]] = typer.Option(
               None, 
               help='release, can be listed multiple times, None for all'),
           species: Optional[List[str]] = typer.Option(
               None, 
               help='valid values are Mm and Hs'),
           resource: Path = typer.Option(
               None, '--resource', '-r', 
               help='ensimpl configuration file'),
           verbose: int = typer.Option(
               0, '--verbose', '-v', count=True)):
    """
    Creates a new ensimpl database <filename> using Ensembl <version>.
    """
    try:
        configure_logging(verbose)
        LOG = get_logger()

        if directory is None:
            directory = os.getcwd()

        if resource is None:
            resource = os.path.dirname(os.path.abspath(__file__))
            resource = os.path.abspath(os.path.join(resource, 'config/ensimpl.ensembl.conf'))

        LOG.info('Creating database...')

        tstart = time.time()
        create_ensimpl.create(release, species, directory, str(resource))
        tend = time.time()

        LOG.info(f'Creation time: {format_time(tstart, tend)}')
    except Exception as e:
        print(e)


@app.command()
def info(release: str = typer.Option(
             None, 
             '--release', '-r',
             help='release'),
         species: str = typer.Option(
             None, 
             '--species', '-s',
             help='valid values are Mm and Hs'),
         verbose: int = typer.Option(
             0, '--verbose', '-v', count=True)):

    """
    Stats annotation database <filename> for <term>
    """
    try:
        configure_logging(verbose)
        LOG = get_logger()
        LOG.debug('Stats database...')

        db = dbs.get_database(release, species, ensimpl_dbs_dict)
        db_meta = meta.db_meta(db)
        statistics = meta.stats(db)

        print(f'Release: {db_meta["release"]}')
        print(f'Species: {db_meta["species"]}, {db_meta["assembly_patch"]}')
        arr = []
        for stat in sorted(statistics):
            arr.append([stat, statistics[stat]])
        print(tabulate(arr))
    except Exception as e:
        print(e)


class SearchOutput(str, Enum):
    tab = 'tab'
    csv = 'csv'
    json = 'json'
    pretty = 'pretty'


@app.command()
def search(term: str = typer.Argument(
               ..., 
               help='search term'),
           release: str = typer.Option(
               None, 
               '--release', '-r',
               help='release'),
           species: str = typer.Option(
               None, 
               '--species', '-s',
               help='valid values are Mm and Hs'),
           exact: bool = typer.Option(
               False, 
               help='exact match or not'),
           format: SearchOutput = typer.Option(
               SearchOutput.pretty, 
               '--format', '-f',
               case_sensitive=False),
           max: int = typer.Option(
               -1,
               '--max', '-m', 
               help='limit the number of matches'),
           verbose: int = typer.Option(
               0, '--verbose', '-v', count=True)):
    """
    Search ensimpl database <filename> for <term>
    """
    configure_logging(verbose)
    LOG = get_logger()
    LOG.info('Search database...')

    maximum = max if max >= 0 else None

    try:
        db = dbs.get_database(release, species, ensimpl_dbs_dict)

        LOG.debug(f'Database: {db}')

        tstart = time.time()
        results = searchdb.search(db, term, exact, maximum)
        tend = time.time()

        LOG.debug(f'Number of Results: {results.num_results}')
        count = 0

        if len(results.matches) == 0:
            print('No results found')
            sys.exit()

        headers = [
            'ID', 
            'SYMBOL', 
            'IDS', 
            'POSITION', 
            'MATCH_REASON',
            'MATCH_VALUE'
        ]
        tbl = []

        if format.value in ('tab', 'csv'):
            delim = '\t' if format.value == 'tab' else ','
            print(delim.join(headers))

        for match in results.matches:
            line = list()
            line.append(match.ensembl_gene_id)
            line.append(match.symbol)

            if match.external_ids:
                ext_ids = []
                for ids in match.external_ids:
                    ext_ids.append(f'{ids["db"]}/{ids["db_id"]}')
                line.append('||'.join(ext_ids))
            else:
                line.append('')

            line.append(f'{match.chromosome}:{match.position_start}-{match.position_end}')
            line.append(match.match_reason)
            line.append(match.match_value)

            if format.value in ('tab', 'csv'):
                print(delim.join(map(str, line)))
            elif format.value == 'json':
                tbl.append(dict(zip(headers, line)))
            else:
                tbl.append(line)

            count += 1
            if count >= max > 0:
                break

        if format.value in ('tab', 'csv'):
            pass
        elif format.value == 'json':
            print(json.dumps({'data': tbl}, indent=4))
        else:
            print(tabulate(tbl, headers))

        LOG.info(f'Search time: {format_time(tstart, tend)}')

    except Exception as e:
        print(e)


@app.command()
def genes(release: str = typer.Option(
              None, 
              '--release', '-r',
              help='release'),
          species: str = typer.Option(
              None, 
              '--species', '-s',
              help='valid values are Mm and Hs'),
          ids: Path = typer.Option(
               None,
               help='text file with Ensembl IDs'),
          format: SearchOutput = typer.Option(
              SearchOutput.pretty, 
              '--format', '-f',
              case_sensitive=False),
          verbose: int = typer.Option(
              0, '--verbose', '-v', count=True)):            
    """
    Get gene information from annotation database.
    """
    try:
        configure_logging(verbose)
        LOG = get_logger()
        LOG.debug(f'Release: {release}')
        LOG.debug(f'Species: {species}')
        LOG.debug(f'Format: {format}')
        LOG.debug(f'IDs: {ids}')

        ensembl_ids = None

        if ids:
            ensembl_ids = []
            with open(ids) as fd:
                for row in fd:
                    row = row.strip()
                    if row:
                        ensembl_ids.append(row.strip().split()[0])

        db = dbs.get_database(release, species, ensimpl_dbs_dict)




        tstart = time.time()
        results = genesdb.get(db, ids=ensembl_ids, details=True)
        tend = time.time()

        headers = [
            'ID', 
            'VERSION', 
            'SPECIES', 
            'SYMBOL', 
            'NAME', 
            'SYNONYMS',
            'EXTERNAL_IDS', 
            'CHR', 
            'START', 
            'END', 
            'STRAND'
        ]

        tbl = []

        delim = '"\t"' if format.value == 'tab' else '","'

        if format.value in ('tab', 'csv'):
            print('"{}"'.format(delim.join(headers)))

        for i in results:
            r = results[i]
            line = list()
            line.append(r['id'])
            line.append(r.get('ensembl_version', ''))
            line.append(r['species_id'])
            line.append(r.get('symbol', ''))
            line.append(r.get('name', ''))
            line.append('||'.join(r.get('synonyms', [])))

            external_ids = r.get('external_ids', [])
            external_ids_str = ''
            if external_ids:
                ext_ids_tmp = []
                for ext in external_ids:
                    ext_ids_tmp.append('{}/{}'.format(ext['db'], ext['db_id']))
                external_ids_str = '||'.join(ext_ids_tmp)
            line.append(external_ids_str)

            line.append(r['chromosome'])
            line.append(r['start'])
            line.append(r['end'])
            line.append(r['strand'])

            if format.value in ('tab', 'csv'):
                print('"{}"'.format(delim.join(map(str, line))))
            elif format.value == 'json':
                tbl.append(r)
            else:
                tbl.append(line)

        if format.value in ('tab', 'csv'):
            pass
        elif format.value == 'json':
            print(json.dumps({'data': tbl}, indent=2))
        else:
            print(tabulate(tbl, headers))
        pass

        LOG.info(f'Search time: {format_time(tstart, tend)}')
    except Exception as e:
        print(e)


@app.command()
def gene(id: str = typer.Argument(
               ..., 
               help='Ensembl ID'),
         release: str = typer.Option(
             None, 
             '--release', '-r',
             help='release'),
         species: str = typer.Option(
             None, 
             '--species', '-s',
             help='valid values are Mm and Hs'),
         format: SearchOutput = typer.Option(
             SearchOutput.pretty, 
             '--format', '-f',
             case_sensitive=False),
          verbose: int = typer.Option(
             0, '--verbose', '-v', count=True)):            
    """
    Get gene information from annotation database.
    """
    try:
        configure_logging(verbose)
        LOG = get_logger()
        LOG.debug(f'Release: {release}')
        LOG.debug(f'Species: {species}')
        LOG.debug(f'Format: {format}')
        LOG.debug(f'ID: {id}')

        ensembl_ids = [id]

        db = dbs.get_database(release, species, ensimpl_dbs_dict)

        tstart = time.time()
        results = genesdb.get(db, ids=ensembl_ids, details=True)
        tend = time.time()

        headers = [
            'ID', 
            'VERSION', 
            'SPECIES', 
            'SYMBOL', 
            'NAME', 
            'SYNONYMS',
            'EXTERNAL_IDS', 
            'CHR', 
            'START', 
            'END', 
            'STRAND'
        ]

        tbl = []

        delim = '"\t"' if format.value == 'tab' else '","'

        if format.value in ('tab', 'csv'):
            print('"{}"'.format(delim.join(headers)))

        for i in results:
            r = results[i]
            line = list()
            line.append(r['id'])
            line.append(r.get('ensembl_version', ''))
            line.append(r['species_id'])
            line.append(r.get('symbol', ''))
            line.append(r.get('name', ''))
            line.append('||'.join(r.get('synonyms', [])))

            external_ids = r.get('external_ids', [])
            external_ids_str = ''
            if external_ids:
                ext_ids_tmp = []
                for ext in external_ids:
                    ext_ids_tmp.append('{}/{}'.format(ext['db'], ext['db_id']))
                external_ids_str = '||'.join(ext_ids_tmp)
            line.append(external_ids_str)

            line.append(r['chromosome'])
            line.append(r['start'])
            line.append(r['end'])
            line.append(r['strand'])

            if format.value in ('tab', 'csv'):
                print('"{}"'.format(delim.join(map(str, line))))
            elif format.value == 'json':
                tbl.append(r)
            else:
                tbl.append(line)

        if format.value in ('tab', 'csv'):
            pass
        elif format.value == 'json':
            print(json.dumps({'data': tbl}, indent=2))
        else:
            print(tabulate(tbl, headers))
        pass

        LOG.info('Search time: {format(format_time(tstart, tend)}')
    except Exception as e:
        print(e)


def main():
    data = dbs.init()
    global ensimpl_dbs
    ensimpl_dbs = data[0]
    global ensimpl_dbs_dict
    ensimpl_dbs_dict = data[1]

    app()


if __name__ == "__main__":
    main()
