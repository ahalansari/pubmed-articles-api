# PubMed Articles API - Complete Documentation

## Overview

A Flask-based REST API for searching PubMed, retrieving open-access articles from PubMed Central, and generating AI-powered clinical summaries using LLM backends.

| Property | Value |
|----------|-------|
| **Base URL** | `http://localhost:8000` |
| **Version** | 1.0.0 |
| **Data Source** | PubMed (35M+ citations) / PubMed Central |
| **Authentication** | API Key via `X-API-Key` header |

---

## Table of Contents

1. [Authentication](#authentication)
2. [Endpoints](#endpoints)
   - [Health Check](#1-health-check)
   - [Search Articles](#2-search-articles)
   - [Retrieve Articles](#3-retrieve-articles)
   - [Get Article by PMID](#4-get-article-by-pmid)
   - [Summarize Articles](#5-summarize-articles)
   - [API Statistics](#6-api-statistics)
   - [API Documentation](#7-api-documentation)
3. [Error Handling](#error-handling)
4. [Configuration](#configuration)
5. [Examples](#examples)

---

## Authentication

All endpoints except `/health` and `/api/v1/docs` require API key authentication.

### Generate API Key

```bash
python generate_api_key.py
```

### Use API Key

Include in request header:

```
X-API-Key: your-api-key-here
```

### Example

```bash
curl -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     http://localhost:8000/api/v1/stats
```

---

## Endpoints

### 1. Health Check

Check API health and service status.

| Property | Value |
|----------|-------|
| **URL** | `/health` |
| **Method** | `GET` |
| **Auth Required** | No |

#### Response

```json
{
  "status": "healthy",
  "service": "PubMed Articles API",
  "version": "1.0.0",
  "data_source": "PubMed/PubMed Central",
  "llm_backend": "lmstudio",
  "llm_status": "available",
  "features": [
    "pubmed_search",
    "open_access_retrieval",
    "llm_search_optimization",
    "article_summaries",
    "demographic_filtering"
  ]
}
```

---

### 2. Search Articles

Search PubMed for articles matching a query.

| Property | Value |
|----------|-------|
| **URL** | `/api/v1/search` |
| **Method** | `POST` |
| **Auth Required** | Yes |
| **Content-Type** | `application/json` |

#### Request Body

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | PubMed search query |
| `limit` | integer | No | 10 | Results to return (1-100) |
| `sort` | string | No | "relevance" | Sort order: "relevance" or "date" |

#### Request Example

```json
{
  "query": "diabetes mellitus type 2 treatment",
  "limit": 10,
  "sort": "relevance"
}
```

#### Response

```json
{
  "query": "diabetes mellitus type 2 treatment",
  "query_translation": "(diabetes mellitus type 2[MeSH]) AND treatment",
  "total_available": 125432,
  "results_count": 10,
  "sort": "relevance",
  "results": [
    {
      "pmid": "38123456",
      "title": "Current Advances in Type 2 Diabetes Management",
      "authors": ["Smith J", "Johnson M", "Williams K"],
      "journal": "Diabetes Care",
      "pub_date": "2024 Jan",
      "doi": "10.2337/dc24-0123",
      "has_pmc": true
    }
  ],
  "_meta": {
    "execution_time_seconds": 0.856
  }
}
```

#### cURL Example

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "acute myocardial infarction diagnosis",
    "limit": 5,
    "sort": "date"
  }'
```

#### PubMed Query Syntax

| Syntax | Example | Description |
|--------|---------|-------------|
| Basic | `hypertension treatment` | Keyword search |
| MeSH | `diabetes mellitus[MeSH]` | MeSH term search |
| Author | `Smith J[Author]` | Author search |
| Date | `2023:2024[dp]` | Date range |
| Journal | `JAMA[Journal]` | Journal filter |
| Title/Abstract | `elderly[tiab]` | Title/abstract search |
| Combined | `(heart failure[MeSH]) AND (elderly[tiab])` | Boolean operators |

---

### 3. Retrieve Articles

Retrieve relevant articles with LLM-powered search optimization and optional AI summaries.

| Property | Value |
|----------|-------|
| **URL** | `/api/v1/retrieve` |
| **Method** | `POST` |
| **Auth Required** | Yes |
| **Content-Type** | `application/json` |

#### Request Body

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `keywords` | array | No* | - | List of search keywords |
| `topic` | string | No* | - | Research topic |
| `case_scenario` | string | No* | - | Clinical case (LLM generates search terms) |
| `patient_age` | integer | No | - | Patient age for context |
| `patient_gender` | string | No | - | Patient gender for context |
| `limit` | integer | No | 5 | Articles to return (1-20) |
| `include_summaries` | boolean | No | false | Generate AI summaries |
| `include_full_text` | boolean | No | false | Include PMC full text |

*At least one of `keywords`, `topic`, or `case_scenario` is required.

#### Request Example (Keywords)

```json
{
  "keywords": ["chest pain", "acute coronary syndrome"],
  "patient_age": 45,
  "patient_gender": "Male",
  "limit": 5,
  "include_summaries": true
}
```

#### Request Example (Case Scenario)

```json
{
  "case_scenario": "58 year old female with type 2 diabetes presenting with non-healing foot ulcer, elevated WBC, and fever",
  "patient_age": 58,
  "patient_gender": "Female",
  "limit": 5,
  "include_summaries": true,
  "include_full_text": true
}
```

#### Response

```json
{
  "search_terms": ["diabetic foot ulcer infection", "osteomyelitis diabetes", "diabetic foot management"],
  "original_input": {
    "keywords": null,
    "topic": null,
    "case_scenario": "58 year old female with type 2 diabetes..."
  },
  "filters": {
    "patient_age": 58,
    "patient_gender": "Female"
  },
  "results_count": 5,
  "include_summaries": true,
  "include_full_text": true,
  "articles": [
    {
      "pmid": "38456789",
      "title": "Management of Diabetic Foot Infections: 2024 Guidelines",
      "authors": ["Garcia R", "Chen L"],
      "journal": "Clinical Infectious Diseases",
      "pub_date": "2024 Feb",
      "abstract": "Diabetic foot infections remain a major cause...",
      "keywords": ["Diabetic Foot", "Osteomyelitis", "Antibiotic Therapy"],
      "mesh_terms": ["Diabetic Foot", "Soft Tissue Infections"],
      "doi": "10.1093/cid/ciae123",
      "pmcid": "PMC9876543",
      "has_full_text": true,
      "full_text": "ABSTRACT:\nDiabetic foot infections...\n\nINTRODUCTION:\n...",
      "summary": "KEY POINTS:\n• Early debridement improves outcomes...\n\nCLINICAL RELEVANCE:\n• For a 58-year-old female diabetic patient..."
    }
  ],
  "_meta": {
    "execution_time_seconds": 12.456,
    "llm_available": true
  }
}
```

#### cURL Example

```bash
curl -X POST http://localhost:8000/api/v1/retrieve \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "case_scenario": "72 year old male with new atrial fibrillation and CKD stage 3",
    "patient_age": 72,
    "patient_gender": "Male",
    "limit": 5,
    "include_summaries": true
  }'
```

---

### 4. Get Article by PMID

Retrieve a specific article by PubMed ID.

| Property | Value |
|----------|-------|
| **URL** | `/api/v1/article/<pmid>` |
| **Method** | `GET` |
| **Auth Required** | Yes |

#### URL Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `pmid` | string | PubMed ID |

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `include_summary` | boolean | false | Generate AI summary |
| `include_full_text` | boolean | false | Include PMC full text |

#### Response

```json
{
  "pmid": "38123456",
  "title": "Current Advances in Type 2 Diabetes Management",
  "authors": ["Smith J", "Johnson M", "Williams K"],
  "journal": "Diabetes Care",
  "pub_date": "2024 Jan",
  "abstract": "Background: Type 2 diabetes mellitus affects millions...",
  "keywords": ["Type 2 Diabetes", "Glycemic Control", "SGLT2 Inhibitors"],
  "mesh_terms": ["Diabetes Mellitus, Type 2", "Hypoglycemic Agents"],
  "doi": "10.2337/dc24-0123",
  "pmcid": "PMC9876543",
  "pub_types": ["Journal Article", "Review"],
  "full_text": "ABSTRACT:\n...\n\nINTRODUCTION:\n...",
  "summary": "KEY POINTS:\n• SGLT2 inhibitors show cardiovascular benefit...",
  "_meta": {
    "execution_time_seconds": 3.456
  }
}
```

#### cURL Examples

```bash
# Basic request
curl -H "X-API-Key: your-api-key" \
     http://localhost:8000/api/v1/article/38123456

# With summary
curl -H "X-API-Key: your-api-key" \
     "http://localhost:8000/api/v1/article/38123456?include_summary=true"

# With summary and full text
curl -H "X-API-Key: your-api-key" \
     "http://localhost:8000/api/v1/article/38123456?include_summary=true&include_full_text=true"
```

---

### 5. Summarize Articles

Generate AI summaries for multiple articles.

| Property | Value |
|----------|-------|
| **URL** | `/api/v1/summarize` |
| **Method** | `POST` |
| **Auth Required** | Yes |
| **Content-Type** | `application/json` |

#### Request Body

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `pmids` | array | Yes | - | Array of PMIDs (max 10) |
| `context` | string | No | - | Clinical context for tailored summaries |
| `combined` | boolean | No | false | Generate combined synthesis |

#### Request Example (Individual Summaries)

```json
{
  "pmids": ["38123456", "38234567", "38345678"]
}
```

#### Request Example (Combined Synthesis)

```json
{
  "pmids": ["38123456", "38234567", "38345678"],
  "context": "Anticoagulation strategy for elderly patients with atrial fibrillation and renal impairment",
  "combined": true
}
```

#### Response (Individual)

```json
{
  "summaries_count": 3,
  "summaries": [
    {
      "pmid": "38123456",
      "title": "DOACs in Elderly Patients with AF",
      "journal": "JACC",
      "has_full_text": true,
      "summary": "KEY POINTS:\n• Reduced-dose DOACs are preferred in CKD...\n\nCLINICAL RELEVANCE:\n• For elderly patients with eGFR 30-50..."
    }
  ],
  "_meta": {
    "execution_time_seconds": 15.234
  }
}
```

#### Response (Combined)

```json
{
  "context": "Anticoagulation strategy for elderly patients...",
  "articles_count": 3,
  "combined_summary": "EVIDENCE SYNTHESIS:\n\nBased on analysis of 3 articles:\n\n1. TREATMENT RECOMMENDATIONS:\n• Apixaban 2.5mg BID preferred for patients with CKD stage 3-4...\n\n2. BLEEDING RISK:\n• HAS-BLED score should guide monitoring frequency...\n\n3. CONSENSUS:\n• All studies support DOAC over warfarin in this population...",
  "_meta": {
    "execution_time_seconds": 8.123
  }
}
```

#### cURL Example

```bash
curl -X POST http://localhost:8000/api/v1/summarize \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "pmids": ["38123456", "38234567"],
    "context": "Treatment of community-acquired pneumonia in immunocompromised patients",
    "combined": true
  }'
```

---

### 6. API Statistics

Get API statistics and capabilities.

| Property | Value |
|----------|-------|
| **URL** | `/api/v1/stats` |
| **Method** | `GET` |
| **Auth Required** | Yes |

#### Response

```json
{
  "service": "PubMed Articles API",
  "version": "1.0.0",
  "data_source": {
    "name": "PubMed/PubMed Central",
    "description": "NCBI's database of biomedical literature",
    "articles_available": "35+ million citations"
  },
  "capabilities": {
    "search": true,
    "open_access_full_text": true,
    "llm_summarization": true,
    "llm_search_optimization": true,
    "chunked_summarization": true,
    "demographic_filtering": true
  },
  "llm_config": {
    "backend": "vllm",
    "model": "meta-llama/Meta-Llama-3-8B-Instruct",
    "context_window": 8192,
    "max_tokens": 2048,
    "max_content_chars": 26672,
    "chunking_enabled": true
  },
  "rate_limits": {
    "ncbi_with_key": "10 requests/second",
    "ncbi_without_key": "3 requests/second"
  }
}
```

---

### 7. API Documentation

Get machine-readable API documentation.

| Property | Value |
|----------|-------|
| **URL** | `/api/v1/docs` |
| **Method** | `GET` |
| **Auth Required** | No |

---

## Error Handling

### Error Response Format

```json
{
  "error": "Error Type",
  "message": "Detailed error message"
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| `200` | Success |
| `400` | Bad Request - Invalid parameters |
| `401` | Unauthorized - Missing/invalid API key |
| `404` | Not Found - Article/endpoint doesn't exist |
| `500` | Internal Server Error |
| `503` | Service Unavailable - LLM backend down |

### Error Examples

**401 - Missing API Key**
```json
{
  "error": "Unauthorized",
  "message": "Valid API key required"
}
```

**400 - Invalid Parameters**
```json
{
  "error": "Bad Request",
  "message": "Must provide at least one of: keywords, topic, or case_scenario"
}
```

**404 - Article Not Found**
```json
{
  "error": "Not Found",
  "message": "Article with PMID 99999999 not found"
}
```

**503 - LLM Unavailable**
```json
{
  "error": "Service Unavailable",
  "message": "LLM backend is not available for summarization"
}
```

---

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `API_KEY` | Authentication key | - | Yes |
| `API_PORT` | Server port | 8000 | No |
| `NCBI_API_KEY` | NCBI key for higher rate limits | - | No |
| `NCBI_EMAIL` | Email for NCBI identification | - | Recommended |
| `LLM_BACKEND` | `lmstudio` or `vllm` | lmstudio | No |
| `LM_STUDIO_BASE_URL` | LM Studio API URL | http://localhost:1234/v1 | No |
| `LM_STUDIO_MODEL` | Model name | default | No |
| `LM_STUDIO_CONTEXT_WINDOW` | Context window size | 8192 | No |
| `VLLM_LLM_BASE_URL` | vLLM API URL | http://localhost:8000/v1 | No |
| `VLLM_LLM_MODEL` | vLLM model name | - | No |
| `VLLM_API_KEY` | vLLM API key | EMPTY | No |
| `VLLM_MAX_TOKENS` | Max response tokens | 2048 | No |
| `VLLM_CONTEXT_WINDOW` | Context window for chunking | 8192 | No |

### Chunked Summarization

For LLM backends with limited context windows (e.g., 8192 tokens), the API automatically:

1. Splits long articles into chunks
2. Summarizes each chunk separately
3. Combines chunk summaries into a coherent final summary

Configure via `VLLM_CONTEXT_WINDOW` or `LM_STUDIO_CONTEXT_WINDOW`.

---

## Examples

### Python Client

```python
import requests

API_URL = "http://localhost:8000"
API_KEY = "your-api-key"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# Search
response = requests.post(
    f"{API_URL}/api/v1/search",
    headers=headers,
    json={"query": "heart failure treatment", "limit": 5}
)
print(response.json())

# Retrieve with case scenario
response = requests.post(
    f"{API_URL}/api/v1/retrieve",
    headers=headers,
    json={
        "case_scenario": "65 year old with dyspnea and bilateral leg edema",
        "patient_age": 65,
        "limit": 3,
        "include_summaries": True
    }
)
for article in response.json()["articles"]:
    print(f"\n{article['title']}")
    print(article.get("summary", "No summary"))

# Combined summary
response = requests.post(
    f"{API_URL}/api/v1/summarize",
    headers=headers,
    json={
        "pmids": ["38123456", "38234567"],
        "context": "Beta-blocker therapy in HFrEF",
        "combined": True
    }
)
print(response.json()["combined_summary"])
```

### JavaScript/Node.js Client

```javascript
const axios = require('axios');

const API_URL = 'http://localhost:8000';
const headers = {
  'X-API-Key': 'your-api-key',
  'Content-Type': 'application/json'
};

// Search
const search = async () => {
  const { data } = await axios.post(
    `${API_URL}/api/v1/search`,
    { query: 'pneumonia antibiotic resistance', limit: 10 },
    { headers }
  );
  console.log(`Found ${data.total_available} articles`);
  return data.results;
};

// Retrieve with summaries
const retrieve = async () => {
  const { data } = await axios.post(
    `${API_URL}/api/v1/retrieve`,
    {
      case_scenario: 'ICU patient with ventilator-associated pneumonia',
      limit: 5,
      include_summaries: true
    },
    { headers }
  );
  
  data.articles.forEach(a => {
    console.log(`\n${a.title}`);
    console.log(a.summary);
  });
};

search();
retrieve();
```

---

## Performance

### Response Times

| Endpoint | Without AI | With AI Summaries |
|----------|------------|-------------------|
| `/search` | 0.5-1.5s | N/A |
| `/retrieve` | 1-3s | 5-25s |
| `/article/<pmid>` | 0.5-1s | 3-5s |
| `/summarize` | N/A | 3-5s per article |

### Best Practices

1. **Get NCBI API key** - 10 req/s instead of 3 req/s
2. **Request summaries only when needed** - Adds 3-5s per article
3. **Use case scenarios** - LLM generates better search terms
4. **Cache aggressively** - PubMed data is relatively stable
5. **Batch summarization** - Use combined mode for synthesis

---

## Rate Limits

| Configuration | Rate Limit |
|---------------|------------|
| Without NCBI API key | 3 requests/second |
| With NCBI API key | 10 requests/second |

Get free NCBI API key: https://www.ncbi.nlm.nih.gov/account/settings/

---

**Version**: 1.0.0  
**Last Updated**: December 2024

