# -*- coding: utf-8 -*-
import io
import os
import time

from collections import namedtuple

import ensimpl.utils as utils
import ensimpl.create.ensembl_db as ensembl_db
import ensimpl.create.ensimpl_db as ensimpl_db

DEFAULT_CONFIG = 'ftp://ftp.jax.org/churchill-lab/ensimpl/ensimpl.ensembl.conf'

ENSEMBL_FIELDS = ['release', 'release_date', 'assembly', 'assembly_patch',
                  'species_id', 'species_name', 'url', 'db', 'compara_db',
                  'server', 'port', 'user_id', 'password']

EnsemblReference = namedtuple('EnsemblReference', ENSEMBL_FIELDS)

LOG = utils.get_logger()


def parse_config(resource_name):
    """Take a resource string (file name, url) and open it.  Parse the file.

    Args:
        resource_name (str): String identifying the resource.

    Returns:
        dict: A ``dict`` with keys being the Ensembl release and values
            of :obj:`EnsemblReference`.
    """
    start = time.time()
    all_releases = {}
    line = ''

    try:
        with utils.open_resource(resource_name) as fd:
            buffer = io.BufferedReader(fd)
            buffer.readline()  # skip first line

            # parse each line and create an EnsemblReference
            for line in buffer:
                line = str(line, 'utf-8')
                elems = line.strip().split('\t')
                if len(elems) < 10:
                    # make sure there is some data on the line
                    continue
                if len(elems) == 12:
                    elems.append(None)
                reference = EnsemblReference(*elems)
                release = all_releases.get(reference.release, {})
                release[reference.species_id] = reference
                all_releases[reference.release] = release

        LOG.info(f'Config parsed in {utils.format_time(start, time.time())}')
    except IOError as io_error:
        LOG.error(f'Unable to access resource: {resource_name}')
        LOG.debug(io_error)
        all_releases = None
    except TypeError as type_error:
        LOG.error(f'Unable to parse resource: {resource_name}')
        LOG.debug(type_error)
        LOG.debug('Error on the following:')
        LOG.debug(line)
        all_releases = None
    except Exception as exc:
        LOG.error(f'Unable to parse resource: {resource_name}')
        LOG.debug(exc)
        LOG.debug('Error on the following:')
        LOG.debug(line)
        all_releases = None

    return all_releases


def create(ensembl, species, directory, resource):
    """Create Ensimpl database(s).  Output database name will be:

    "ensembl. ``release`` . ``species`` .db3"

    Args:
        ensembl (list): A ``list`` of all Ensembl releases to create, ``None``
            for all.
        species (list): A ``list`` of all species to create, ``None`` for all.
        directory (str): Output directory.
        resource (str): Configuration file location to parse.
    """
    if ensembl:
        LOG.debug('Ensembl Releases: {}'.format(','.join(ensembl)))
    else:
        LOG.debug('Ensembl Releases: ALL')

    LOG.debug(f'Directory: {directory}')
    LOG.debug(f'Resource: {resource}')

    releases = parse_config(resource)

    if not releases:
        LOG.error('Unable to determine the Ensembl releases and locations '
                  'for download')
        LOG.error(f'Please make sure that the resource "{resource}"'
                  'is accessible and in the correct format')
        raise Exception("Unable to create databases")

    if ensembl:
        all_releases = list(releases.keys())
        all_releases.sort()
        not_found = list(set(ensembl) - set(all_releases))
        if not_found:
            not_found.sort()
            LOG.error(f'Unable to determine the Ensembl release specified: '
                      f'{", ".join(not_found)}')
            LOG.error(f'Please make sure that the resource "{resource}" is '
                      'accessible and in the correct format')
            LOG.error(f'Found Ensembl releases: {", ".join(all_releases)}')
            raise Exception('Unable to create databases')

    for release_ver, release_val in sorted(releases.items()):
        if ensembl and release_ver not in ensembl:
            continue

        for species_id, ensembl_ref in sorted(release_val.items()):
            if not species or (species_id in species):
                LOG.warning('Generating ensimpl database for Ensembl '
                            f'release: {release_ver}')

                ensimpl_file = f'ensimpl.{release_ver}.{species_id}.db3'

                ensimpl_file = os.path.join(directory, ensimpl_file)
                utils.delete_file(ensimpl_file)

                LOG.info(f'Creating: {ensimpl_file}')

                ensimpl_db.initialize(ensimpl_file)

                LOG.info('Extracting chromosomes...')
                chromosomes_karyotypes = \
                    ensembl_db.extract_chromosomes_karyotypes(ensembl_ref)
    
                LOG.info('Extracting genes...')
                genes = ensembl_db.extract_ensembl_genes(ensembl_ref)
    
                LOG.info('Extracting synonyms...')
                synonyms = ensembl_db.extract_synonyms(ensembl_ref)
    
                LOG.info('Extracting transcript, protein, and exons...')
                gtep = ensembl_db.extract_ensembl_gtpe(ensembl_ref)
    
                LOG.info('Extracting homologs...')
                homologs = ensembl_db.extract_ensembl_homologs(ensembl_ref)

                LOG.info('Inserting chromsomes...')
                ensimpl_db.insert_chromosomes_karyotypes(ensimpl_file,
                                                         ensembl_ref,
                                                         chromosomes_karyotypes)
    
                LOG.info('Inserting genes...')
                ensimpl_db.insert_genes(ensimpl_file,
                                        ensembl_ref,
                                        genes,
                                        synonyms,
                                        homologs)
    
                LOG.info('Inserting transcript, protein, and exons...')
                ensimpl_db.insert_gtpe(ensimpl_file,
                                       ensembl_ref,
                                       gtep)
    
                LOG.info('Inserting homologs...')
                ensimpl_db.insert_homologs(ensimpl_file,
                                           ensembl_ref,
                                           homologs)

                LOG.info('Finalizing...')
                ensimpl_db.finalize(ensimpl_file,
                                    ensembl_ref)

    LOG.info('DONE')


