# syntax=docker/dockerfile:1
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN python -m pip install -U pip \
    && pip install -r requirements.txt
COPY . .
EXPOSE 9100
CMD ["python","-m","uvicorn","src.api.server:app","--host","0.0.0.0","--port","9100"]
