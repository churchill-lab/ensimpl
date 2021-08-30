Debugging with Reload

```
uvicorn ensimpl.main:app --reload
```

Speed Testing

```
apib -c 100 -d 20 "https://churchilllab.jax.org/ensimpltest/searchapi2?species=Mm&release=90&term=Ace"
ab  -n 1000 -c 100 "http://127.0.0.1/searchapi2?species=Mm&release=90&term=Ace"
```


Docker Building

```
docker build -t mattjvincent/ensimpl:1.0.0 .
docker push mattjvincent/ensimpl:1.0.0
```


Notes

Refactor some things:

    * make app creation a factory?
    * is routers/api.py where it should be
    * GZIPMiddlewear has no compression level

```
@router.post("/genesdebug")
async def genes_post(request: Request, response: Response):

    for h in request.headers:
        print(h, request.headers[h])

    b = await request.body()
    print(b)

    return({'body':b.decode()})


class GQ(BaseModel):
    release: str
    species: str              
    ids: List[str]
    details: Optional[bool] = False


@router.post("/genesmodel")
async def genes_model(request: Request, response: Response, gq: GQ):
    """
    curl: ACCEPTS json 
        curl --header "Content-Type: application/json" --request POST \
             -g --data '{"species":"Mm","release":"90","ids":["ENSMUSG00000020681","ENSMUSG00000101605"],"details":false}' \
             http://127.0.0.1:8000/api/genesmodel
    form: No because it's url encoded and not json
    ajax: Yes 
            $.ajax({
                url: '/api/genesjson',
                type: "POST",
                data: JSON.stringify(data),
                // contentType is a must because it defaults to application/x-www-form-urlencoded
                contentType:"application/json; charset=utf-8",
            })
            b'{"release":"98","species":"Mm","ids":["ENSMUSG00000113812","ENSMUSG00000097853","ENSMUSG00000009090"],"details":false}'
    """
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





@router.post("/genesjson")
async def genes_json(request: Request, response: Response):
    """
    curl: ACCEPTS json 
        curl --header "Content-Type: application/json" --request POST \
             -g --data '{"species":"Mm","release":"90","ids":["ENSMUSG00000020681","ENSMUSG00000101605"],"details":false}' \
             http://127.0.0.1:8000/api/genesjson
    form: No because it's url encoded and not json
    ajax: Yes
            $.ajax({
                url: '/api/genesjson',
                type: "POST",
                data: JSON.stringify(data),
                // doesn't have to be set, server tries to just parse the data into json
                contentType:"application/json; charset=utf-8",
            })
            b'{"release":"98","species":"Mm","ids":["ENSMUSG00000113812","ENSMUSG00000097853","ENSMUSG00000009090"],"details":false}'
    """
    ret = {}

    try:
        ids = None
        release = None
        species = None
        details = False

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
        return {'message': str(e)}

    return ret

    return {"message": message, "received_data_as_json": json_data}


@router.post("/genesform")
async def genes_form(request: Request, response: Response,
                    release: str = Form(...), species: str = Form(...),
                    ids: List[str] = Form(...),
                    details: Optional[bool] = Form(...)):
    """
    curl: ACCEPTS application/x-www-form-urlencoded 
        curl 'http://127.0.0.1:8000/api/genesform' \
        -H 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8' \
        --data-raw 'release=98&species=Mm&ids=ENSMUSG00000113812&ids=ENSMUSG00000097853&ids=ENSMUSG00000009090&details=false' \
    form: YES because it's url encoded and not json
    ajax: Yes
            $.ajax({
                url: '/api/genesform',
                type: "POST",
                // keep tradional = true, otherwise the ids parameter
                // will be encoded to ids[]
                traditional: true,
                data: data
            })
            b'release=98&species=Mm&ids=ENSMUSG00000113812&ids=ENSMUSG00000097853&ids=ENSMUSG00000009090&details=false'
    """
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



```