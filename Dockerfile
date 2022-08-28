FROM python:slim

COPY ./src .
COPY .env .env
COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt