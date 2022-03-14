import os

from fastapi import FastAPI
from fastapi import Request
from fastapi import Response
from fastapi import status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional


from ensimpl.fastapi_utils import GZipCompressionMiddleware
from ensimpl.routers import api
import ensimpl.db.dbs as dbs

template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'templates')
templates = Jinja2Templates(directory=template_dir)

static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

# TODO: maybe a factory
# figure out config and what all the options do
app = FastAPI(
    title='Ensimpl',
    description='Quicker Ensembl',
    version='1.0.0',
    root_path=os.environ.get('ROOT_PATH'))

app.mount('/static', StaticFiles(directory=static_dir), name='static')


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request,
                                       exc: RequestValidationError):
    for h in request.headers:
        print(h, request.headers[h])

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({'detail': exc.errors(), 'body': exc.body}),
    )


origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# this is added because starlette does not support compression_level in GZip
# they do in 0.15, but fastapi doesn't require that version yet
app.add_middleware(
    GZipCompressionMiddleware,
    minimum_size=1000,
    compression_level=3
)

app.include_router(api.router)


@app.on_event('startup')
async def startup():
    ensimpl_dbs, ensimpl_dbs_dict = dbs.init()
    app.state.dbs = ensimpl_dbs
    app.state.dbs_dict = ensimpl_dbs_dict
    app.state.url_prefix = ''
    if os.environ.get('URL_PREFIX') is not None:
        app.state.url_prefix = os.environ.get('URL_PREFIX')


@app.get('/', response_class=HTMLResponse)
async def index_html(request: Request):
    return templates.TemplateResponse('index.html',
                                      {'request': request, 'app': app})


@app.get('/ping')
async def ping_json():
    return {'ping': 'ok'}


@app.get('/favicon.ico')
async def favicon():
    file_name = 'favicon.ico'
    file_path = os.path.join(static_dir, file_name)
    return FileResponse(path=file_path,
                        headers={
                            'Content-Disposition':
                                f'attachment; filename={file_name}'
                        })


@app.get('/search', response_class=HTMLResponse)
async def search_html(request: Request, response: Response,
    term: Optional[str] = None, release: Optional[str] = None, species: Optional[str] = None,
    greedy: Optional[bool] = False, exec: Optional[bool] = False):

    options = {
        'request': request,
        'term': '' if term is None else term,
        'release': '' if release is None else release,
        'species': '' if species is None else str(species).lower(),
        'greedy': 'false' if greedy is None else str(greedy).lower(),
        'exec': 'false' if greedy is None else str(exec).lower(),
        'app': app
    }

    return templates.TemplateResponse('search.html', options)


@app.get('/navigator', response_class=HTMLResponse)
async def navigator_html(request: Request):
    return templates.TemplateResponse('navigator.html',
                                      {'request': request, 'app': app})


@app.get('/lookup', response_class=HTMLResponse)
async def lookup_html(request: Request):
    return templates.TemplateResponse('lookup.html',
                                      {'request': request, 'app': app})


@app.get('/external_ids', response_class=HTMLResponse)
async def external_ids_html(request: Request):
    return templates.TemplateResponse('external_ids.html',
                                      {'request': request, 'app': app})


@app.get('/history', response_class=HTMLResponse)
async def history_html(request: Request):
    return templates.TemplateResponse('history.html',
                                      {'request': request, 'app': app})


@app.get('/help', response_class=HTMLResponse)
async def help_html(request: Request):
    return templates.TemplateResponse('help.html',
                                      {'request': request, 'app': app})


@app.get('/js/karyotype.js', response_class=HTMLResponse)
async def karyotype_js(request: Request):
    return templates.TemplateResponse('karyotype.js',
                                      {'request': request, 'app': app},
                                      media_type='application/javascript')


@app.get('/js/ensimpl.js', response_class=HTMLResponse)
async def ensimpl_js(request: Request):
    return templates.TemplateResponse('ensimpl.js',
                                      {'request': request, 'app': app},
                                      media_type='application/javascript')
