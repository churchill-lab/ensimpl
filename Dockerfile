FROM tiangolo/uvicorn-gunicorn-fastapi:python3.7
LABEL maintainer="Matthew Vincent <mattjvincent@gmail.com>" \
	  version="1.0.0"

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY ./ensimpl /app/ensimpl


