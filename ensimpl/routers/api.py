# Standard library imports
import inspect
import json
from datetime import datetime
from functools import wraps
from json import JSONDecodeError
from typing import Any
from typing import List
from typing import Optional

# 3rd party imports
import orjson
from fastapi import APIRouter
from fastapi import Form
from fastapi import Request
from fastapi import Response
from fastapi import status
from fastapi.responses import JSONResponse
from fastapi.responses import ORJSONResponse
from fastapi.responses import UJSONResponse
from natsort import natsorted
from pydantic import BaseModel

# local imports
from ensimpl import utils
from ensimpl.db import dbs
from ensimpl.db import genes as genesdb
from ensimpl.db import meta
from ensimpl.db import search as searchdb

router = APIRouter(
    prefix="/api",
    tags=["api"],
    responses={404: {"description": "API not found"}},
)


def default(obj):
    """
    Custom parser for orjson (usually named default)
    """
    if isinstance(obj, datetime):
        return str(obj)
    raise TypeError


class CustomORJSONResponse(ORJSONResponse):
    """
    Custom orjson response with a custom format for datetimes

    orjson defaults to outputing datetime objects in RFC 3339 format:
        `1970-01-01T00:00:00+00:00`

    with this, we simply output the string representation of the python
        datetime object:
        `1970-01-01 00:00:00`

    see: https://github.com/ijl/orjson#opt_passthrough_datetime
    """

    def render(self, content: Any) -> bytes:
        assert orjson is not None, \
            "orjson must be installed to use ORJSONResponse"
        return orjson.dumps(
            content, option=orjson.OPT_PASSTHROUGH_DATETIME, default=default
        )


class CustomJSONResponse(JSONResponse):
    """ JSONResponse that handles datetimes. A little slower than orjson """

    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            default=default,
        ).encode("utf-8")


def go_fast(f):
    """Skips FastAPI's slow `jsonable_encoder` and `serialize_response` and
    converts content not wrapped in a response into a ORJSONResponse w/ custom
    datetime serialization
    """

    @wraps(f)
    async def a_wrapped(*args, **kwargs):
        return CustomORJSONResponse(await f(*args, **kwargs))

    @wraps(f)
    def wrapped(*args, **kwargs):
        return CustomORJSONResponse(f(*args, **kwargs))

    if inspect.iscoroutinefunction(f):
        return a_wrapped
    else:
        return wrapped


@router.get("/releases")
async def releases(request: Request, response: Response):
    """
    Get all the release and species information.

    If successful, a JSON response will be returned with a single
    **release** element containing a **list** of releases consisting of the
    following items:

    | Element | Type | Description | 
    |--|--|--|
    | release | str | the Ensembl release |
    | species | str | the species identifier (example 'Hs', 'Mm') |
    | assembly | str | the genome assembly information |
    | assembly_patch | str | the genome assembly patch number |

    If an error occurs, a JSON response will be sent back with just one
    element called **message** along with a status code of **404**.
    """
    ret = []

    try:
        for database in request.app.state.dbs:
            ret.append({
                'release': database['release'],
                'species': database['species'],
                'greedy_release': database['greedy_release'],
                'assembly': database['assembly'],
                'assembly_patch': database['assembly_patch'],
                'url': database['url']
            })
    except Exception as e:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {'message': str(e)}

    return CustomORJSONResponse(ret)


@router.get("/stats")
async def stats(request: Request, response: Response,
                release: str, species: str):
    """
    Get the information for a particular Ensembl release and species.

    If successful, a JSON response will be returned with a single
    **release** element containing a **list** of releases consisting of the
    following items:

    | Element | Type | Description | 
    |--|--|--|
    | release | str | the Ensembl release |
    | species | str | the species identifier (example 'Hs', 'Mm') |
    | assembly | str | the genome assembly information |
    | assembly_patch | str | the genome assembly patch number |
    | stats | dict | various stats about the database |

    If an error occurs, a JSON response will be sent back with just one
    element called **message** along with a status code of **404**.
    """
    ret = {}

    try:
        db = dbs.get_database(release, species, request.app.state.dbs_dict)
        ret['meta'] = meta.db_meta(db)
        ret['stats'] = meta.stats(db)
    except Exception as e:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {'message': str(e)}

    return CustomORJSONResponse(ret)


@router.get("/chromosomes")
async def chromosomes(request: Request, response: Response,
                      release: str, species: str):
    """
    If successful, a JSON response will be returned with a single
    **chromosomes** element containing a **list** of chromosomes consisting
    of the following items:

    | Element | Type | Description | 
    |--|--|--|
    | chromosome | str | the chromsome |
    | length | int | length in base pairs |
    | order | int | order in the genome |

    If an error occurs, a JSON response will be sent back with just one
    element called **message** along with a status code of **404**.
    """
    ret = {}

    try:
        db = dbs.get_database(release, species, request.app.state.dbs_dict)
        ret['meta'] = meta.db_meta(db)
        ret['chromosomes'] = meta.chromosomes(db)
    except Exception as e:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {'message': str(e)}

    return CustomORJSONResponse(ret)


@router.get("/karyotypes")
async def karyotypes(request: Request, response: Response,
                     release: str, species: str):
    """
    If successful, a JSON response will be returned with a single
    **chromosomes** element containing a **list** of chromosomes consisting
    of the following items:

    | Element | Type | Description | 
    |--|--|--|
    | chromosome | str | the chromsome |
    | length | int | length in base pairs |
    | order | int | order in the genome |
    | karyotypes | list | list of **karyotype_elements** |

    A **karyotype_element** contains the following items:

    | Element | Type | Description | 
    |--|--|--|
    | band | str | name of the band |
    | seq_region_start | int | start position |
    | seq_region_end | int | end position |
    | stain | string | name of the stain |


    If an error occurs, a JSON response will be sent back with just one
    element called **message** along with a status code of **404**.
    """
    ret = {}

    try:
        db = dbs.get_database(release, species, request.app.state.dbs_dict)
        ret['meta'] = meta.db_meta(db)
        ret['chromosomes'] = meta.karyotypes(db)
    except Exception as e:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {'message': str(e)}

    return CustomORJSONResponse(ret)


@router.get("/gene/{ensembl_id}")
async def gene(request: Request, response: Response,
               ensembl_id: str, release: str, species: str,
               details: Optional[bool] = False):
    """
    Get the information for an Ensembl gene.

    The following is a list of the valid query parameters:

    =======  =======  ===================================================
    Param    Type     Description
    =======  =======  ===================================================
    release  string   the Ensembl release
    species  string   the species identifier (example 'Hs', 'Mm')
    details  string   true, false, T, F, 0, 1
    =======  =======  ===================================================

    If successful, a JSON response will be returned with a single ``gene``
    element consisting the following items:

    =================  =======  ============================================
    Element            Type     Description
    =================  =======  ============================================
    id                 string   Ensembl gene identifier
    ensembl_version    integer  version of the identifier
    species_id         string   species identifier: 'Mm', 'Hs', etc
    chromosome         string   the chromosome
    start              integer  start position in base pairs
    end                integer  end position in base pairs
    strand             string   '+' or '-'
    name               string   name of the gene
    symbol             string   gene symbol
    synonyms           list     list of strings
    external_ids       list     each having keys of 'db' and 'db_id'
    homolog_ids        list     each having keys of 'homolog_id' and
                                'homolog_symbol'
    transcripts        list     each having a ``transcript`` element
    =================  =======  ============================================

    ``transcript_element``, with each item containing:

    =================  =======  ============================================
    Element            Type     Description
    =================  =======  ============================================
    id                 string   Ensembl transcript identifier
    ensembl_version    integer  version of the identifier
    symbol             string   transcript symbol
    start              integer  start position in base pairs
    end                integer  end position in base pairs
    exons              list     dict of: number,id,start,end,ensembl_version
    protein            dict     id, start, end, ensembl_version
    =================  =======  ============================================

    If the id is not found, the gene will still be returned but have
    ``null`` for a value.

    If an error occurs, a JSON response will be sent back with just one
    element called ``message`` along with a status code of 500.

    Returns:
        :class:`flask.Response`: The response which is a JSON response.
    """
    ret = {}

    try:
        db = dbs.get_database(release, species, request.app.state.dbs_dict)
        ret['meta'] = meta.db_meta(db)

        results = genesdb.get(db, ids=[ensembl_id], details=details)

        if len(results) == 0:
            raise Exception(f'No results found for: {ensembl_id}')

        if len(results) > 1:
            raise ValueError(f'Too many genes found for: {ensembl_id}')

        ret['gene'] = results
    except Exception as e:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {'message': str(e)}

    return CustomORJSONResponse(ret)


class GQ(BaseModel):
    release: str
    species: str
    ids: List[str]
    details: Optional[bool] = False


@router.post("/genesmodel")
async def genes_model(request: Request, response: Response, gq: GQ):
    ret = {}

    try:
        db = dbs.get_database(gq.release, gq.species,
                              request.app.state.dbs_dict)
        ret['meta'] = meta.db_meta(db)

        results = genesdb.get(db, ids=gq.ids, details=gq.details)

        if len(results) == 0:
            raise Exception(f'No results found')

        ret['genes'] = results
    except Exception as e:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {'message': str(e)}

    return ret


@router.post("/genesdebug")
async def genes_post(request: Request):
    for h in request.headers:
        print(h, request.headers[h])

    b = await request.body()
    print(b)

    return {
        'body': b.decode()
    }


@router.post("/genes")
async def genes_json(request: Request, response: Response):
    """
    Will accept the following
    """
    ret = {}

    try:
        json_data = await request.json()

        if 'release' in json_data:
            release = json_data['release']
        else:
            raise Exception('release value is missing')

        if 'species' in json_data:
            species = json_data['species']
        else:
            raise Exception('species value is missing')

        if 'ids' in json_data:
            ids = json_data['ids']
        elif 'ids[]' in json_data:
            # this is for backwards compatibility with ensimplR
            ids = json_data['ids[]']
        else:
            raise Exception('ids value is missing')

        if 'details' in json_data:
            details = utils.str2bool(json_data['details'])
        else:
            details = False

        db = dbs.get_database(release, species, request.app.state.dbs_dict)
        ret['meta'] = meta.db_meta(db)

        results = genesdb.get(db, ids=ids, details=details)

        if len(results) == 0:
            raise Exception(f'No results found')

        ret['genes'] = results
    except JSONDecodeError as e:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {
            'message': 'Received data is not a valid JSON',
            'detail': str(e)
        }
    except Exception as e:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {
            'message': str(e)
        }

    return CustomORJSONResponse(ret)


@router.post("/genesform")
async def genes_form(request: Request, response: Response,
                     release: str = Form(...), species: str = Form(...),
                     ids: List[str] = Form(...),
                     details: Optional[bool] = Form(...)):
    ret = {}

    try:
        db = dbs.get_database(release, species, request.app.state.dbs_dict)
        ret['meta'] = meta.db_meta(db)

        results = genesdb.get(db, ids=ids, details=details)

        if len(results) == 0:
            raise Exception(f'No results found')

        ret['genes'] = results
    except Exception as e:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {'message': str(e)}

    return ret


@router.post("/external_ids")
async def external_ids(request: Request, response: Response):
    """
    Get the information for an Ensembl gene.

    The following is a list of the valid parameters:

    ========  =======  ===================================================
    Param     Type     Description
    ========  =======  ===================================================
    ids       list     repeated id elements, one per Ensembl id
    source_db string   Defaults to 'Ensembl', but other are valid, please see
                       external_dbs().
    release   string   the Ensembl release
    species   string   the species identifier (example 'Hs', 'Mm')
    ========  =======  ===================================================

    If successful, a JSON response will be returned with multiple ``gene``
    elements, each consisting of the following items:

    =================  =======  ============================================
    Element            Type     Description
    =================  =======  ============================================
    id                 string   Ensembl gene identifier
    ensembl_version    integer  version of the identifier
    =================  =======  ============================================


    If an id is not found, the gene will still be returned but have
    ``null`` for a value.

    If an error occurs, a JSON response will be sent back with just one
    element called ``message`` along with a status code of 500.

    Returns:
        :class:`flask.Response`: The response which is a JSON response.
    """
    ret = {}

    try:
        ids = None
        release = None
        species = None
        source_db = None

        json_data = await request.json()

        if 'release' in json_data:
            release = json_data['release']
        else:
            raise Exception('release value is missing')

        if 'species' in json_data:
            species = json_data['species']
        else:
            raise Exception('species value is missing')

        if 'ids' in json_data:
            ids = json_data['ids']
        else:
            raise Exception('ids value is missing')

        if 'source_db' in json_data:
            source_db = json_data['source_db']
        else:
            source_db = 'Ensembl'

        db = dbs.get_database(release, species, request.app.state.dbs_dict)
        ret['meta'] = meta.db_meta(db)

        results = genesdb.get_ids(db, ids=ids, source_db=source_db)

        if len(results) == 0:
            raise Exception(f'No results found')

        ret['ids'] = results
    except Exception as e:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {'message': str(e)}

    return CustomORJSONResponse(ret)


@router.get("/search", response_class=UJSONResponse)
async def search(request: Request, response: Response,
                 term: str, release: str, species: str,
                 exact: Optional[bool] = False, limit: Optional[int] = 100000,
                 greedy: Optional[bool] = False):
    """
    Perform a search of a Ensimpl database.

    The following is a list of the valid parameters:

    =======  =======  ===================================================
    Param    Type     Description
    =======  =======  ===================================================
    term     string   the term to search for
    release  string   the Ensembl release
    species  string   the species identifier (example 'Hs', 'Mm')
    exact    string   to exact match or not, defaults to 'False'
    limit    string   max number of items to return, defaults to 100,000
    greedy   string   to perform greedy search (amx assembly for release)
    =======  =======  ===================================================

    If sucessful, a JSON response will be returned with the following elements:

    =======  =======  ===================================================
    Element  Type     Description
    =======  =======  ===================================================
    request  dict     the request parameters
    result   dict     the results
    =======  =======  ===================================================

    The ``request`` dictionary will have the same values as listed above in the
    valid parameters.

    The ``result`` dictionary will have the following elements:

    ============  =======  ===================================================
    Element       Type     Description
    ============  =======  ===================================================
    num_results   int      the total number of matches
    num_matches   int      the number of matches returned (limited by limit)
    matches       list     a list of match objects
    ============  =======  ===================================================

    Each match object will contain:

    ================  =======  ===============================================
    Element           Type     Description
    ================  =======  ===============================================
    match_reason      string   reason of the match: name, synonym, id, etc
    match_value       string   value that matched
    ensembl_gene_id   string   Ensembl gene identifier
    ensembl_version   integer  version of the identifier
    chromosome        string   the chromosome
    position_start    integer  start position in base pairs
    position_end      integer  end position in base pairs
    strand            string   '+' or '-'
    species           string   species identifier: 'Mm', 'Hs', etc
    name              string   name of the gene
    symbol            string   gene symbol
    synonyms          list     list of strings
    external_ids      list     each having keys of 'db' and 'db_id
    ================  =======  ===============================================

    If an error occurs, a JSON response will be sent back with just one
    element called ``message`` along with a status code of 500.

    Returns:
        :class:`flask.Response`: The response which is a JSON response.
    """
    ret = {}

    try:
        db = dbs.get_database(release, species, request.app.state.dbs_dict, greedy)

        ret['meta'] = meta.db_meta(db)

        ret['request'] = {
            'term': term,
            'species': species,
            'exact': exact,
            'limit': limit,
            'release': release,
            'greedy': greedy
        }

        ret['result'] = {
            'num_results': 0,
            'num_matches': 0,
            'matches': None
        }

        results = searchdb.search(db, term, exact, limit)

        if len(results.matches) == 0:
            raise Exception(f'No results found for: {term}')

        ret['result']['num_results'] = results.num_results
        ret['result']['num_matches'] = results.num_matches
        ret['result']['matches'] = []

        for match in results.matches:
            ret['result']['matches'].append(match.dict())

    except Exception as e:
        # TODO: better handling and logging
        # response.status_code = status.HTTP_404_NOT_FOUND
        # print(str(e))
        pass

    return CustomORJSONResponse(ret)


@router.get("/history")
async def history(request: Request, response: Response,
                  ensembl_id: str, species: str,
                  release_start: str, release_end: str):
    """
    Perform a search of an Ensimpl Identifier.

    The following is a list of the valid parameters:

    id, species, version_start=None, version_end=None, full=False):

    =============  =======  ===================================================
    Param          Type     Description
    =============  =======  ===================================================
    id             string   the Ensembl id
    species        string   the species identifier (example 'Hs', 'Mm')
    version_start  integer  the start version to search for
    version_end    integer  the end version to search for
    =============  =======  ===================================================

    If sucessful, a JSON response will be returned with the following elements:


    Returns:
        :class:`flask.Response`: The response which is a JSON response.
    """
    ret = {}

    try:
        ret['request'] = {
            'ensembl_id': ensembl_id,
            'species': species,
            'release_start': release_start,
            'release_end': release_end
        }

        start_idx = -1
        end_idx = 100000
        for x, db in enumerate(request.app.state.dbs):
            rel = db['release']
            if rel == release_start:
                start_idx = max(x, start_idx)
            if rel == release_end:
                end_idx = min(x, end_idx)

        all_dbs = request.app.state.dbs[end_idx:start_idx + 1]

        databases = []
        for database in all_dbs:
            if species == database['species']:
                databases.append(database['db'])

        results = genesdb.get_history(databases, ensembl_id)

        if len(results) == 0:
            raise Exception(f'No results found for: {ensembl_id}')

        ret['history'] = results

    except Exception as e:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {'message': str(e)}

    return CustomORJSONResponse(ret)


@router.get("/external_dbs")
async def external_dbs(request: Request, response: Response,
                       release: str, species: str):
    """Get the external database information.

    The following is a list of the valid parameters:

    =======  =======  ===================================================
    Param    Type     Description
    =======  =======  ===================================================
    release  string   the Ensembl release
    species  string   the species identifier (example 'Hs', 'Mm')
    =======  =======  ===================================================

    If successful, a JSON response will be returned with a single
    ``external_dbs`` element containing a ``list`` of external databases
    consisting of the following items:

    =================  =======  ============================================
    Element            Type     Description
    =================  =======  ============================================
    external_db_id     string   unique external db identifier
    external_db_name   string   external db name
    ranking_id         string   internal ranking id
    =================  =======  ============================================

    If an error occurs, a JSON response will be sent back with just one
    element called ``message`` along with a status code of 500.

    """
    ret = {}

    try:
        db = dbs.get_database(release, species, request.app.state.dbs_dict)
        ret['meta'] = meta.db_meta(db)
        ret['external_dbs'] = meta.external_dbs(db)
    except Exception as e:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {'message': str(e)}

    return CustomORJSONResponse(ret)


@router.get("/randomids")
async def randomids(request: Request, response: Response,
                    release: str, species: str,
                    source_db: str = 'Ensembl', limit: int = 10):
    """
    Get random ids.  Mostly useful for examples.

    No parameters are needed, but the following are allowed:

    ========  =======  ===================================================
    Param     Type     Description
    ========  =======  ===================================================
    version   integer  the Ensembl version number
    species   string   the species identifier (example 'Hs', 'Mm')
    num       integer  Number of ids to return.
    source_db string   Defaults to 'Ensembl', but other are valid, please see
                       external_dbs().
    ========  =======  ===================================================

    If successful, a JSON response will be returned with an array of IDs.

    If an error occurs, a JSON response will be sent back with just one
    element called ``message`` along with a status code of 500.

    Returns:
        :class:`flask.Response`: The response which is a JSON response.
    """
    ret = {}

    try:
        db = dbs.get_database(release, species, request.app.state.dbs_dict)
        ret['meta'] = meta.db_meta(db)

        ret['ids'] = genesdb.random_ids(db, source_db, limit)
    except Exception as e:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {'message': str(e)}

    return CustomORJSONResponse(ret)


@router.get("/exon_info")
async def exon_info(request: Request, response: Response,
                    release: str, species: str,
                    chrom: Optional[str] = None,
                    compress: Optional[bool] = False):
    """

    """
    ret = {}

    try:
        db = dbs.get_database(release, species, request.app.state.dbs_dict)
        ret['meta'] = meta.db_meta(db)
        ret['genes'] = genesdb.get_exon_info(db, chrom, compress)
    except Exception as e:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {'message': str(e)}

    return CustomORJSONResponse(ret)
