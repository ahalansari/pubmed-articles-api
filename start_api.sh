#!/bin/bash

# PubMed Articles API Startup Script
# ==================================

echo ""
echo "🚀 PubMed Articles API Startup"
echo "=============================="
echo ""

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "📦 Activating virtual environment..."
    source .venv/bin/activate
else
    echo "⚠️  No virtual environment found. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from template..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "📝 Created .env from .env.example"
        echo "   Please edit .env to set your API_KEY"
    else
        echo "❌ No .env.example found. Please create .env file."
        exit 1
    fi
fi

# Load environment variables
set -a
source .env
set +a

# Check for API key
if [ -z "$API_KEY" ] || [ "$API_KEY" = "your-api-key-here" ]; then
    echo ""
    echo "⚠️  WARNING: No API key configured!"
    echo "   Generate one with: python generate_api_key.py"
    echo "   Or run without authentication for testing"
    echo ""
fi

# Start the server
echo ""
echo "Starting API server on port ${API_PORT:-8000}..."
echo ""
python api_server.py

