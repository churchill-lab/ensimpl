# -*- coding: utf-8 -*-
import glob
import os
import sys

from ensimpl.utils import multikeysort

ENSIMPL_DB_NAME = 'ensimpl.*.db3'


def get_all_ensimpl_dbs(directory):
    """Configure the list of ensimpl db files in `directory`.  This will set
    values for :data:`ENSIMPL_DBS` and :data:`ENSIMPL_DBS_DICT`.

    Args:
        directory (str): The directory path.
    """
    databases = glob.glob(os.path.join(directory, ENSIMPL_DB_NAME))

    db_list = []
    db_dict = {}

    for db in databases:
        # db should be a string consisting of the following elements:
        # 'ensimpl', version, species, 'db3'
        val = {
            'release': int(db.split('.')[1]),
            'species': db.split('.')[2],
            'db': db
        }
        db_list.append(val)

        # combined key will be 'release:species'
        combined_key = f'{val["release"]}:{val["species"]}'
        db_dict[combined_key] = val

    # sort the databases in descending order by version and than species for
    # readability in the API
    all_sorted_dbs = multikeysort(db_list, ['-release', 'species'])

    return (all_sorted_dbs, db_dict)


def init(directory=None):
    """Initialize the configuration of the Ensimpl databases.

    NOTE: This method is referenced from the ``__init__.py`` in this module.

    Args:
        directory (str, optional): A directory that specifies where the ensimpl
            databases live. If None the environment variable ``ENSIMPL_DIR``
            will be used.
    """
    ensimpl_dir = os.environ.get('ENSIMPL_DIR', None)

    if directory:
        ensimpl_dir = directory

    if not ensimpl_dir:
        print('ENSIMPL_DIR not configured in environment or directory '
              'was not supplied as an option')
        raise Exception('ENSIMPL_DIR not configured in environment or directory '
              'was not supplied as an option')

    if not os.path.isabs(ensimpl_dir):
        ensimpl_dir = os.path.abspath(os.path.join(os.getcwd(), ensimpl_dir))
    else:
        ensimpl_dir = os.path.abspath(ensimpl_dir)

    if not os.path.exists(ensimpl_dir):
        print('Specified ENSIMPL_DIR does not exits')
        print(f'ENSIMPL_DIR = "{ensimpl_dir}"')
        raise Exception('Specified ENSIMPL_DIR does not exits')

    if not os.path.isdir(ensimpl_dir):
        print('Specified ENSIMPL_DIR is not a directory')
        print(f'ENSIMPL_DIR = "{ensimpl_dir}"')
        raise Exception('Specified ENSIMPL_DIR is not a directory')

    return get_all_ensimpl_dbs(ensimpl_dir)



def get_database(release, species, dbs):
    """
    Connect to the Ensimpl database.

    Args:
        release (str): The Ensembl release.
        species (str): The Ensembl species identifier.
        dbs (dict): The Ensimpl dbs.

    Returns:
        a connection to the database
    """
    try:
        return dbs[f'{release}:{species}']['db']        
    except Exception as e:
        ensimpl_dir = os.environ.get('ENSIMPL_DIR', None)
        raise Exception(f'Unable to find database: '
                        f'release {release}, species {species}, '
                        f'ENSIMPL_DIR {ensimpl_dir}')


def get_release_species(db):
    """
    Connect to the Ensimpl database.

    Args:
        db (str): The Ensimpl database.
    Returns:
        a dict with elements release and species
    """
    try:
        val = {
            'release': int(db.split('.')[1]),
            'species': db.split('.')[2]
        }

        return val
    except Exception as e:
        raise Exception(f'Unable to determine release and species from {db}')

