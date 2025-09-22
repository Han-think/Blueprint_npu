# multi-stage: runtime만 포함
FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN python -m pip install -U pip && pip install -r requirements.txt
COPY . .
EXPOSE 9001 9018 9019 9030
CMD ["uvicorn","app.ui:app","--host","0.0.0.0","--port","9030"]
