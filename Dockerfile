# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN pip install -U pip && pip install -r requirements.txt

EXPOSE 9001 9002 9003 9004 9005 9006 9007 9008 9010 9011 9012 9013 9014
ENV BLUEPRINT_FAKE=1

CMD ["uvicorn", "app.moo:app", "--host", "0.0.0.0", "--port", "9007"]

