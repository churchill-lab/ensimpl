from typing import Dict
from typing import Optional
from typing import Tuple
import glob
import os

import natsort

from ensimpl.utils import multikeysort
from ensimpl.db import meta

ENSIMPL_DB_NAME = 'ensimpl.*.db3'


def get_all_ensimpl_dbs(directory: str) -> Tuple:
    """Configure the list of ensimpl db files in `directory`.  This will set
    values for :data:`ENSIMPL_DBS` and :data:`ENSIMPL_DBS_DICT`.

    Args:
        directory (str): The directory path.
    """
    databases = glob.glob(os.path.join(directory, ENSIMPL_DB_NAME))

    max_assembly = {}
    temp_list = []

    for db in databases:
        meta_info = meta.db_meta(db)
        assembly = meta_info['assembly']
        release = meta_info['release']
        species = meta_info['species']
        combined_key = f'{assembly}:{species}'

        # db should be a string consisting of the following elements:
        # 'ensimpl', release, species, 'db3'
        val = {
            'db': db,
            'species': species,
            'release': release,
            'assembly': assembly,
            'assembly_patch': meta_info['assembly_patch'],
            'url': meta_info['url'],
            'greedy_release': None
        }

        release = int(release)

        max_assembly[combined_key] = max(max_assembly.get(combined_key, release),
                                         release)

        temp_list.append(val)

    db_list = []
    db_dict = {}

    for db in temp_list:
        combined_key_assembly = f'{db["assembly"]}:{db["species"]}'
        db['greedy_release'] = max_assembly[combined_key_assembly]
        db_list.append(db)

        # combined key will be 'release:species'
        combined_key = f'{db["release"]}:{db["species"]}'
        db_dict[combined_key] = db

    # sort the databases in descending order by version and then species for
    # readability in the API
    all_sorted_dbs = \
        natsort.natsorted(db_list, key=lambda e: (e['release'], e['species']))
    all_sorted_dbs = list(reversed(all_sorted_dbs))

    return all_sorted_dbs, db_dict


def init(directory: Optional[str] = None) -> Tuple:
    """Initialize the configuration of the Ensimpl databases.

    Args:
        directory: A directory that specifies where the ensimpl
            databases live. If None the environment variable ``ENSIMPL_DIR``
            will be used.

    Returns:
        A tuple with all information anout the databases.
    """
    ensimpl_dir = os.environ.get('ENSIMPL_DIR', None)

    if directory:
        ensimpl_dir = directory

    if not ensimpl_dir:
        print('ENSIMPL_DIR not configured in environment or directory '
              'was not supplied as an option')
        raise Exception('ENSIMPL_DIR not configured in environment or '
                        'directory was not supplied as an option')

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


def get_database(release: str, species: str, dbs: dict,
                 greedy: Optional[bool] = False) -> str:
    """
    Connect to the Ensimpl database.

    Args:
        release: The Ensembl release.
        species: The Ensembl species identifier.
        dbs: The Ensimpl dbs.
        greedy: True to search latest assembly for a release.

    Returns:
        The sqlite database.
    """
    try:
        if greedy:
            release = dbs[f'{release}:{species}']['greedy_release']

        return dbs[f'{release}:{species}']['db']
    except Exception:
        ensimpl_dir = os.environ.get('ENSIMPL_DIR', None)
        raise Exception(f'Unable to find database: '
                        f'release {release}, species {species}, '
                        f'ENSIMPL_DIR {ensimpl_dir}')


def get_release_species(db: str) -> Dict[str, str]:
    """
    Connect to the Ensimpl database.

    Args:
        db: The Ensimpl database.
    Returns:
        A dict with elements release and species.
    """
    try:
        val = {
            'release': db.split('.')[1],
            'species': db.split('.')[2]
        }

        return val
    except Exception:
        raise Exception(f'Unable to determine release and species from {db}')
