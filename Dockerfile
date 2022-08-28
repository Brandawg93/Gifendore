FROM python:slim

COPY . .
RUN pip install -r requirements.txt