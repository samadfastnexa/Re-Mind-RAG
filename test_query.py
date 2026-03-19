#!/usr/bin/env python3
"""Test script to query the RAG system"""
import requests
import json

# Login
login_response = requests.post(
    "http://localhost:8001/api/auth/login",
    data={"username": "admin", "password": "admin123"},
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)
login_response.raise_for_status()
token = login_response.json()["access_token"]
print(f"✓ Login successful, token: {token[:20]}...")

# Query
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}
query_data = {
    "question": "what is theft policy?",
    "top_k": 6
}

print(f"\n🔍 Querying: '{query_data['question']}'")
query_response = requests.post(
    "http://localhost:8001/query",
    headers=headers,
    json=query_data,
    timeout=60
)
query_response.raise_for_status()
result = query_response.json()

# Display results
print(f"\n📝 Answer ({result.get('answer_type', 'default')}):")
print(result["answer"])
print(f"\n📚 Sources: {len(result['sources'])} chunks retrieved")
if result.get('retrieval_metadata'):
    meta = result['retrieval_metadata']
    print(f"   - Hybrid search: {meta.get('hybrid_search_used', False)}")
    print(f"   - Reranking: {meta.get('reranking_used', False)}")

print("\n✅ Query test successful!")
