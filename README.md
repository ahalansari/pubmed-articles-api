# PubMed Articles API

Flask-based REST API for searching PubMed, retrieving open-access articles from PubMed Central, and generating AI-powered clinical summaries.

## Features

- 🔍 **PubMed Search** - Search 35+ million biomedical citations
- 📄 **Open Access Retrieval** - Automatic full-text from PubMed Central
- 🤖 **LLM-Powered Search** - AI generates optimal search terms from case scenarios
- 📝 **Clinical Summaries** - AI-generated structured summaries with chunking support
- 👤 **Demographic Filtering** - Context-aware results (age/gender)

## Quick Start

### Local Development

```bash
# Clone and setup
git clone https://github.com/YOUR_USERNAME/pubmed-articles-api.git
cd pubmed-articles-api

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp env_example.txt .env
python generate_api_key.py  # Add key to .env

# Start (ensure LM Studio is running)
python api_server.py
```

### Docker

```bash
# Build and run
docker build -t pubmed-articles-api .
docker run -d \
  -p 8000:8000 \
  -e API_KEY="your-api-key" \
  -e LM_STUDIO_BASE_URL="http://host.docker.internal:1234/v1" \
  pubmed-articles-api
```

### Docker Compose

```bash
# Copy and edit .env
cp env_example.txt .env
# Edit .env with your settings

# Run
docker-compose up -d
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check (no auth) |
| `/api/v1/search` | POST | Search PubMed |
| `/api/v1/retrieve` | POST | AI-optimized retrieval with summaries |
| `/api/v1/article/<pmid>` | GET | Get specific article |
| `/api/v1/summarize` | POST | Batch summarization |
| `/api/v1/stats` | GET | API capabilities |
| `/api/v1/docs` | GET | API documentation (no auth) |

## Example Usage

```bash
# Search PubMed
curl -X POST http://localhost:8000/api/v1/search \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"query": "diabetes treatment", "limit": 5}'

# Retrieve with AI summaries
curl -X POST http://localhost:8000/api/v1/retrieve \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "case_scenario": "45 year old male with chest pain",
    "patient_age": 45,
    "patient_gender": "Male",
    "limit": 3,
    "include_summaries": true
  }'
```

## Unraid Installation

1. Add the template URL to Community Applications:
   ```
   https://raw.githubusercontent.com/YOUR_USERNAME/pubmed-articles-api/main/pubmed-articles-api.xml
   ```

2. Configure:
   - Set your API key
   - Point to your LM Studio or vLLM instance
   - Optionally add NCBI API key for higher rate limits

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `API_KEY` | Authentication key | Required |
| `API_PORT` | Server port | 8000 |
| `NCBI_API_KEY` | NCBI key (10 req/s vs 3) | Optional |
| `LLM_BACKEND` | `lmstudio` or `vllm` | lmstudio |
| `LM_STUDIO_BASE_URL` | LM Studio API URL | http://localhost:1234/v1 |
| `VLLM_CONTEXT_WINDOW` | Context window for chunking | 8192 |

## LLM Backend Requirements

This API requires an LLM backend for:
- Generating optimized search terms
- Selecting relevant articles
- Summarizing articles

Supported backends:
- **LM Studio** (recommended for local development)
- **vLLM** (recommended for production)

## Documentation

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for complete API documentation.

## License

MIT

