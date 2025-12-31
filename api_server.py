"""
PubMed Articles API Server
Flask-based RESTful API for searching PubMed and retrieving open-access articles
with LLM-powered summarization and search optimization
"""

import os
import time
import secrets
import hashlib
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from pubmed_client import PubMedClient
from llm_client import LLMClient

load_dotenv()

app = Flask(__name__)
CORS(app)

API_KEY = os.getenv("API_KEY", "")
API_PORT = int(os.getenv("API_PORT", "8000"))
LLM_BACKEND = os.getenv("LLM_BACKEND", "lmstudio")
NCBI_API_KEY = os.getenv("NCBI_API_KEY", "")
NCBI_EMAIL = os.getenv("NCBI_EMAIL", "")

pubmed_client = None
llm_client = None


def init_clients():
    """Initialize PubMed and LLM clients"""
    global pubmed_client, llm_client
    
    pubmed_client = PubMedClient(
        api_key=NCBI_API_KEY if NCBI_API_KEY else None,
        email=NCBI_EMAIL if NCBI_EMAIL else None
    )
    
    try:
        llm_client = LLMClient(backend=LLM_BACKEND)
        llm_available = llm_client.health_check()
    except Exception:
        llm_client = None
        llm_available = False
    
    return llm_available


def require_api_key(f):
    """Decorator to require API key authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not API_KEY:
            return f(*args, **kwargs)
        
        provided_key = request.headers.get("X-API-Key", "")
        
        if not provided_key:
            return jsonify({
                "error": "Unauthorized",
                "message": "Valid API key required"
            }), 401
        
        if not secrets.compare_digest(provided_key, API_KEY):
            return jsonify({
                "error": "Unauthorized",
                "message": "Invalid API key"
            }), 401
        
        return f(*args, **kwargs)
    return decorated


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint - no authentication required"""
    llm_status = "available" if llm_client and llm_client.health_check() else "unavailable"
    
    return jsonify({
        "status": "healthy",
        "service": "PubMed Articles API",
        "version": "1.0.0",
        "data_source": "PubMed/PubMed Central",
        "llm_backend": LLM_BACKEND,
        "llm_status": llm_status,
        "features": [
            "pubmed_search",
            "open_access_retrieval",
            "llm_search_optimization",
            "article_summaries",
            "demographic_filtering"
        ]
    })


@app.route("/api/v1/search", methods=["POST"])
@require_api_key
def search_articles():
    """
    Search PubMed for articles
    
    Request body:
    {
        "query": "diabetes mellitus",
        "limit": 10,
        "sort": "relevance"
    }
    """
    start_time = time.time()
    
    data = request.get_json() or {}
    query = data.get("query", "").strip()
    limit = data.get("limit", 10)
    sort = data.get("sort", "relevance")
    
    if not query:
        return jsonify({
            "error": "Bad Request",
            "message": "query parameter is required"
        }), 400
    
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        return jsonify({
            "error": "Bad Request",
            "message": "limit must be an integer between 1 and 100"
        }), 400
    
    if sort not in ["relevance", "date"]:
        return jsonify({
            "error": "Bad Request",
            "message": "sort must be 'relevance' or 'date'"
        }), 400
    
    try:
        search_result = pubmed_client.search(query, max_results=limit, sort=sort)
        pmids = search_result.get("pmids", [])
        
        if pmids:
            articles = pubmed_client.get_article_summaries(pmids)
        else:
            articles = []
        
        results = []
        for article in articles:
            results.append({
                "pmid": article.get("pmid"),
                "title": article.get("title"),
                "authors": article.get("authors", []),
                "journal": article.get("journal"),
                "pub_date": article.get("pub_date"),
                "doi": article.get("doi"),
                "has_pmc": bool(article.get("pmcid"))
            })
        
        return jsonify({
            "query": query,
            "query_translation": search_result.get("query_translation", query),
            "total_available": search_result.get("total_count", 0),
            "results_count": len(results),
            "sort": sort,
            "results": results,
            "_meta": {
                "execution_time_seconds": round(time.time() - start_time, 3)
            }
        })
        
    except Exception as e:
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@app.route("/api/v1/retrieve", methods=["POST"])
@require_api_key
def retrieve_articles():
    """
    Retrieve relevant PubMed articles with optional AI summaries
    
    Request body:
    {
        "keywords": ["chest pain", "acute coronary syndrome"],
        "topic": "cardiac arrest management",
        "case_scenario": "45 year old male with chest pain",
        "patient_age": 45,
        "patient_gender": "Male",
        "limit": 5,
        "include_summaries": true,
        "include_full_text": true
    }
    """
    start_time = time.time()
    
    data = request.get_json() or {}
    keywords = data.get("keywords", [])
    topic = data.get("topic", "").strip()
    case_scenario = data.get("case_scenario", "").strip()
    patient_age = data.get("patient_age")
    patient_gender = data.get("patient_gender")
    limit = data.get("limit", 5)
    include_summaries = data.get("include_summaries", False)
    include_full_text = data.get("include_full_text", False)
    
    if not keywords and not topic and not case_scenario:
        return jsonify({
            "error": "Bad Request",
            "message": "Must provide at least one of: keywords, topic, or case_scenario"
        }), 400
    
    if not isinstance(limit, int) or limit < 1 or limit > 20:
        return jsonify({
            "error": "Bad Request",
            "message": "limit must be an integer between 1 and 20"
        }), 400
    
    try:
        search_terms = []
        context = ""
        
        if case_scenario and llm_client:
            search_terms = llm_client.generate_search_terms(case_scenario=case_scenario)
            context = case_scenario
        elif topic and llm_client:
            search_terms = llm_client.generate_search_terms(topic=topic)
            context = topic
        elif keywords:
            search_terms = keywords
            context = " ".join(keywords)
        else:
            search_terms = [topic] if topic else [case_scenario]
            context = topic or case_scenario
        
        if not search_terms:
            search_terms = keywords if keywords else [topic or case_scenario]
        
        all_pmids = set()
        all_articles = []
        
        for term in search_terms[:5]:
            search_result = pubmed_client.search(term, max_results=20, sort="relevance")
            pmids = search_result.get("pmids", [])
            for pmid in pmids:
                if pmid not in all_pmids:
                    all_pmids.add(pmid)
        
        if all_pmids:
            articles = pubmed_client.get_article_details(list(all_pmids)[:50])
            all_articles = articles
        
        if llm_client and len(all_articles) > limit:
            selected_pmids = llm_client.select_relevant_articles(all_articles, context, limit)
            selected_articles = []
            for pmid in selected_pmids:
                for a in all_articles:
                    if str(a.get("pmid")) == str(pmid):
                        selected_articles.append(a)
                        break
            all_articles = selected_articles
        else:
            all_articles = all_articles[:limit]
        
        if include_full_text or include_summaries:
            pmids_to_convert = [a.get("pmid") for a in all_articles]
            pmcid_map = pubmed_client.convert_pmid_to_pmcid(pmids_to_convert)
            
            for article in all_articles:
                pmid = str(article.get("pmid"))
                if pmid in pmcid_map:
                    article["pmcid"] = pmcid_map[pmid]
                    if include_full_text:
                        full_text = pubmed_client.get_pmc_full_text(pmcid_map[pmid])
                        if full_text:
                            article["full_text"] = full_text
        
        if include_summaries and llm_client:
            patient_context = {}
            if patient_age:
                patient_context["age"] = patient_age
            if patient_gender:
                patient_context["gender"] = patient_gender
            
            for article in all_articles:
                summary = llm_client.summarize_article(article, patient_context if patient_context else None)
                article["summary"] = summary
        
        results = []
        for article in all_articles:
            result = {
                "pmid": article.get("pmid"),
                "title": article.get("title"),
                "authors": article.get("authors", []),
                "journal": article.get("journal"),
                "pub_date": article.get("pub_date"),
                "abstract": article.get("abstract"),
                "keywords": article.get("keywords", []),
                "mesh_terms": article.get("mesh_terms", []),
                "doi": article.get("doi"),
                "pmcid": article.get("pmcid"),
                "has_full_text": "full_text" in article
            }
            
            if include_full_text and "full_text" in article:
                result["full_text"] = article["full_text"]
            
            if include_summaries and "summary" in article:
                result["summary"] = article["summary"]
            
            results.append(result)
        
        return jsonify({
            "search_terms": search_terms,
            "original_input": {
                "keywords": keywords if keywords else None,
                "topic": topic if topic else None,
                "case_scenario": case_scenario if case_scenario else None
            },
            "filters": {
                "patient_age": patient_age,
                "patient_gender": patient_gender
            },
            "results_count": len(results),
            "include_summaries": include_summaries,
            "include_full_text": include_full_text,
            "articles": results,
            "_meta": {
                "execution_time_seconds": round(time.time() - start_time, 3),
                "llm_available": llm_client is not None
            }
        })
        
    except Exception as e:
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@app.route("/api/v1/article/<pmid>", methods=["GET"])
@require_api_key
def get_article(pmid):
    """
    Get a specific article by PMID
    
    Query parameters:
    - include_summary: boolean (default: false)
    - include_full_text: boolean (default: false)
    """
    start_time = time.time()
    
    include_summary = request.args.get("include_summary", "false").lower() == "true"
    include_full_text = request.args.get("include_full_text", "false").lower() == "true"
    
    try:
        articles = pubmed_client.get_article_details([pmid])
        
        if not articles:
            return jsonify({
                "error": "Not Found",
                "message": f"Article with PMID {pmid} not found"
            }), 404
        
        article = articles[0]
        
        pmcid_map = pubmed_client.convert_pmid_to_pmcid([pmid])
        if pmid in pmcid_map:
            article["pmcid"] = pmcid_map[pmid]
            if include_full_text:
                full_text = pubmed_client.get_pmc_full_text(pmcid_map[pmid])
                if full_text:
                    article["full_text"] = full_text
        
        if include_summary and llm_client:
            article["summary"] = llm_client.summarize_article(article)
        
        result = {
            "pmid": article.get("pmid"),
            "title": article.get("title"),
            "authors": article.get("authors", []),
            "journal": article.get("journal"),
            "pub_date": article.get("pub_date"),
            "abstract": article.get("abstract"),
            "keywords": article.get("keywords", []),
            "mesh_terms": article.get("mesh_terms", []),
            "doi": article.get("doi"),
            "pmcid": article.get("pmcid"),
            "pub_types": article.get("pub_types", [])
        }
        
        if include_full_text and "full_text" in article:
            result["full_text"] = article["full_text"]
        
        if include_summary and "summary" in article:
            result["summary"] = article["summary"]
        
        result["_meta"] = {
            "execution_time_seconds": round(time.time() - start_time, 3)
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@app.route("/api/v1/summarize", methods=["POST"])
@require_api_key
def summarize_articles():
    """
    Generate AI summaries for multiple articles
    
    Request body:
    {
        "pmids": ["12345678", "87654321"],
        "context": "optional clinical context"
    }
    """
    start_time = time.time()
    
    if not llm_client:
        return jsonify({
            "error": "Service Unavailable",
            "message": "LLM backend is not available for summarization"
        }), 503
    
    data = request.get_json() or {}
    pmids = data.get("pmids", [])
    context = data.get("context", "").strip()
    combined = data.get("combined", False)
    
    if not pmids:
        return jsonify({
            "error": "Bad Request",
            "message": "pmids array is required"
        }), 400
    
    if len(pmids) > 10:
        return jsonify({
            "error": "Bad Request",
            "message": "Maximum 10 articles can be summarized at once"
        }), 400
    
    try:
        articles = pubmed_client.get_article_details(pmids)
        
        if not articles:
            return jsonify({
                "error": "Not Found",
                "message": "No articles found for the provided PMIDs"
            }), 404
        
        pmcid_map = pubmed_client.convert_pmid_to_pmcid(pmids)
        for article in articles:
            pmid = str(article.get("pmid"))
            if pmid in pmcid_map:
                article["pmcid"] = pmcid_map[pmid]
                full_text = pubmed_client.get_pmc_full_text(pmcid_map[pmid])
                if full_text:
                    article["full_text"] = full_text
        
        if combined and context:
            combined_summary = llm_client.generate_combined_summary(articles, context)
            return jsonify({
                "context": context,
                "articles_count": len(articles),
                "combined_summary": combined_summary,
                "_meta": {
                    "execution_time_seconds": round(time.time() - start_time, 3)
                }
            })
        
        summaries = []
        for article in articles:
            summary = llm_client.summarize_article(article)
            summaries.append({
                "pmid": article.get("pmid"),
                "title": article.get("title"),
                "journal": article.get("journal"),
                "has_full_text": "full_text" in article,
                "summary": summary
            })
        
        return jsonify({
            "summaries_count": len(summaries),
            "summaries": summaries,
            "_meta": {
                "execution_time_seconds": round(time.time() - start_time, 3)
            }
        })
        
    except Exception as e:
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@app.route("/api/v1/stats", methods=["GET"])
@require_api_key
def get_stats():
    """Get API statistics and capabilities"""
    llm_config = llm_client.get_config() if llm_client else None
    
    return jsonify({
        "service": "PubMed Articles API",
        "version": "1.0.0",
        "data_source": {
            "name": "PubMed/PubMed Central",
            "description": "NCBI's database of biomedical literature",
            "articles_available": "35+ million citations"
        },
        "capabilities": {
            "search": True,
            "open_access_full_text": True,
            "llm_summarization": llm_client is not None,
            "llm_search_optimization": llm_client is not None,
            "chunked_summarization": llm_client is not None,
            "demographic_filtering": True
        },
        "llm_config": llm_config,
        "rate_limits": {
            "ncbi_with_key": "10 requests/second",
            "ncbi_without_key": "3 requests/second"
        }
    })


@app.route("/api/v1/docs", methods=["GET"])
def get_docs():
    """API documentation endpoint - no authentication required"""
    return jsonify({
        "name": "PubMed Articles API",
        "version": "1.0.0",
        "description": "RESTful API for searching PubMed and retrieving open-access articles with AI-powered summarization",
        "base_url": f"http://localhost:{API_PORT}",
        "authentication": {
            "type": "API Key",
            "header": "X-API-Key",
            "required_for": "All endpoints except /health and /api/v1/docs"
        },
        "endpoints": [
            {
                "path": "/health",
                "method": "GET",
                "description": "Health check",
                "auth_required": False
            },
            {
                "path": "/api/v1/search",
                "method": "POST",
                "description": "Search PubMed for articles",
                "auth_required": True,
                "parameters": {
                    "query": "string (required) - Search query",
                    "limit": "integer (1-100, default: 10) - Number of results",
                    "sort": "string ('relevance' or 'date', default: 'relevance')"
                }
            },
            {
                "path": "/api/v1/retrieve",
                "method": "POST",
                "description": "Retrieve relevant articles with AI summaries",
                "auth_required": True,
                "parameters": {
                    "keywords": "array - List of search keywords",
                    "topic": "string - Research topic",
                    "case_scenario": "string - Clinical case description",
                    "patient_age": "integer - Patient age for context",
                    "patient_gender": "string - Patient gender",
                    "limit": "integer (1-20, default: 5) - Number of articles",
                    "include_summaries": "boolean (default: false) - Generate AI summaries",
                    "include_full_text": "boolean (default: false) - Include full text if available"
                }
            },
            {
                "path": "/api/v1/article/<pmid>",
                "method": "GET",
                "description": "Get specific article by PMID",
                "auth_required": True,
                "parameters": {
                    "include_summary": "boolean (default: false)",
                    "include_full_text": "boolean (default: false)"
                }
            },
            {
                "path": "/api/v1/summarize",
                "method": "POST",
                "description": "Generate AI summaries for multiple articles",
                "auth_required": True,
                "parameters": {
                    "pmids": "array (required) - List of PMIDs (max 10)",
                    "context": "string - Clinical context for summaries",
                    "combined": "boolean (default: false) - Generate combined summary"
                }
            },
            {
                "path": "/api/v1/stats",
                "method": "GET",
                "description": "Get API statistics and capabilities",
                "auth_required": True
            }
        ]
    })


@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "error": "Not Found",
        "message": "The requested endpoint does not exist"
    }), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({
        "error": "Internal Server Error",
        "message": "An unexpected error occurred"
    }), 500


def main():
    print("\n🚀 Starting PubMed Articles API Server...")
    print("=" * 60)
    
    print("Initializing clients...")
    llm_available = init_clients()
    
    print(f"✅ PubMed client ready")
    if llm_available:
        print(f"✅ LLM backend ({LLM_BACKEND}) ready")
    else:
        print(f"⚠️  LLM backend ({LLM_BACKEND}) unavailable - summarization disabled")
    
    if API_KEY:
        print("🔒 API Key authentication enabled")
    else:
        print("⚠️  API Key authentication disabled (set API_KEY in .env)")
    
    if NCBI_API_KEY:
        print("✅ NCBI API key configured (10 req/sec)")
    else:
        print("⚠️  No NCBI API key (limited to 3 req/sec)")
    
    print(f"📚 API documentation: http://localhost:{API_PORT}/api/v1/docs")
    print("=" * 60)
    
    app.run(host="0.0.0.0", port=API_PORT, debug=False)


if __name__ == "__main__":
    main()

