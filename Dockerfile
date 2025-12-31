FROM python:3.11-slim

LABEL maintainer="PubMed Articles API"
LABEL description="Flask API for searching PubMed with LLM-powered summarization"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py .

ENV PYTHONUNBUFFERED=1
ENV API_PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "api_server.py"]

