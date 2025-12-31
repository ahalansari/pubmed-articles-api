#!/usr/bin/env python3
"""
API Key Generator for PubMed Articles API
Generates secure API keys for authentication
"""

import secrets
import string
import hashlib
import sys
from datetime import datetime


def generate_api_key(length: int = 40) -> str:
    """Generate a cryptographically secure API key"""
    alphabet = string.ascii_letters + string.digits
    key = ''.join(secrets.choice(alphabet) for _ in range(length))
    return key


def hash_key(key: str) -> str:
    """Generate a hash of the API key for storage/verification"""
    return hashlib.sha256(key.encode()).hexdigest()


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        key = generate_api_key()
        print(key)
        return
    
    print("\n" + "=" * 60)
    print("🔐 PubMed Articles API Key Generator")
    print("=" * 60)
    print()
    
    key = generate_api_key()
    key_hash = hash_key(key)
    
    print("✅ API Key Generated Successfully!")
    print()
    print(f"API Key: {key}")
    print()
    print("⚠️  SAVE THIS KEY - You won't see it again!")
    print()
    print("-" * 60)
    print("Add to your .env file:")
    print("-" * 60)
    print(f'API_KEY="{key}"')
    print()
    print("-" * 60)
    print("Key Hash (for verification):")
    print("-" * 60)
    print(key_hash)
    print()
    print("=" * 60)
    print(f"Generated: {datetime.now().isoformat()}")
    print("=" * 60)


if __name__ == "__main__":
    main()

