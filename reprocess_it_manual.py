"""
Helper script to re-process the IT Department Manual with SOP chunking.

This script will:
1. Delete the old document (with 658-char fixed chunks)
2. Re-upload it with the new SOP processor (procedure-based chunks)
3. Verify the chunks are better

Run: python reprocess_it_manual.py
"""
import requests
import os
from pathlib import Path

# Configuration
API_URL = "http://localhost:8001"
PDF_PATH = input("Enter path to '(Revised) IT Department Manual.pdf': ").strip().strip('"')

# Get authentication token
print("\n🔐 Login to get authentication token...")
username = input("Username (default: admin): ").strip() or "admin"
password = input("Password (default: admin123): ").strip() or "admin123"

# Login
response = requests.post(
    f"{API_URL}/api/auth/login",
    data={"username": username, "password": password},
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)

if response.status_code != 200:
    print(f"❌ Login failed: {response.text}")
    exit(1)

token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print(f"✅ Logged in successfully")

# Get list of documents
print("\n📄 Fetching current documents...")
response = requests.get(f"{API_URL}/documents", headers=headers)
documents = response.json()

# Find the IT Department Manual
old_doc = None
for doc in documents:
    if "IT Department Manual" in doc["filename"] or "ITD" in doc["filename"]:
        old_doc = doc
        break

if old_doc:
    print(f"📋 Found old document: {old_doc['filename']}")
    print(f"   Document ID: {old_doc['document_id']}")
    print(f"   Chunks: {old_doc['chunks']}")
    print(f"   Upload Date: {old_doc['upload_date']}")
    
    # Delete old document
    confirm = input(f"\n⚠️  Delete old document '{old_doc['filename']}'? (yes/no): ")
    if confirm.lower() == 'yes':
        response = requests.delete(
            f"{API_URL}/documents/{old_doc['document_id']}",
            headers=headers
        )
        if response.status_code == 200:
            print(f"✅ Deleted old document")
        else:
            print(f"❌ Failed to delete: {response.text}")
            exit(1)
    else:
        print("⏭️  Skipping deletion, will upload as new document")
else:
    print("ℹ️  Old document not found, will upload as new")

# Upload the document with auto-detection
print(f"\n📤 Uploading document with SOP auto-detection...")

# Check if file exists
if not Path(PDF_PATH).exists():
    print(f"❌ File not found: {PDF_PATH}")
    print("\nPlease provide the correct path to '(Revised) IT Department Manual.pdf'")
    exit(1)

with open(PDF_PATH, 'rb') as f:
    files = {'file': (Path(PDF_PATH).name, f, 'application/pdf')}
    data = {'processing_mode': 'auto'}  # Will auto-detect SOP
    
    response = requests.post(
        f"{API_URL}/upload",
        headers=headers,
        files=files,
        data=data
    )

if response.status_code != 200:
    print(f"❌ Upload failed: {response.text}")
    exit(1)

result = response.json()
print(f"\n✅ Upload successful!")
print(f"   Document ID: {result.get('document_id', 'N/A')}")
print(f"   Filename: {result.get('filename', 'N/A')}")
print(f"   Pages: {result.get('pages', 'N/A')}")
print(f"   Chunks: {result.get('chunks', 'N/A')}")

# Test a query
print(f"\n🧪 Testing query to verify improvement...")
test_query = "What is the process for purchasing new hardware?"

response = requests.post(
    f"{API_URL}/query",
    headers={**headers, "Content-Type": "application/json"},
    json={"question": test_query, "top_k": 5}
)

if response.status_code == 200:
    result = response.json()
    print(f"\n📊 Query Results:")
    print(f"   Question: {result['question']}")
    print(f"   Sources: {len(result['sources'])}")
    print(f"\n   Top Source:")
    if result['sources']:
        top_source = result['sources'][0]
        print(f"   - Document: {top_source['document']}")
        print(f"   - Chunk: {top_source['chunk']}/{top_source['total_chunks']}")
        print(f"   - Relevance: {top_source['relevance_score']:.3f}")
        if 'procedure_no' in top_source:
            print(f"   - Procedure No: {top_source.get('procedure_no', 'N/A')}")
        if 'section_id' in top_source:
            print(f"   - Section: {top_source.get('section_id', 'N/A')}")
        print(f"\n   Content Preview:")
        content = top_source['content'][:500]
        print(f"   {content}{'...' if len(top_source['content']) > 500 else ''}")
    
    print(f"\n   Answer:")
    print(f"   {result['answer'][:500]}{'...' if len(result['answer']) > 500 else ''}")
else:
    print(f"❌ Query failed: {response.text}")

print(f"\n✅ Re-processing complete!")
print(f"\nNext steps:")
print(f"  1. View the document at: http://localhost:3000/documents")
print(f"  2. Click to see individual chunks (should now be procedure-based)")
print(f"  3. Test more queries in the chat interface")
