"""Check if table data from IT User Manual is indexed in ChromaDB"""
import sys
sys.path.insert(0, 'rag_system')

from app.services.vector_store import vector_store

# Search for LCD Repair
print("=" * 80)
print("SEARCHING FOR: LCD Repair")
print("=" * 80)
results = vector_store.similarity_search('LCD Repair expected time completion days', top_k=10)
print(f"\nTotal results: {len(results)}\n")

for i, r in enumerate(results, 1):
    meta = r.get('metadata', {})
    content = r.get('content', '')
    print(f"#{i} - Page {meta.get('page', 'N/A')} | Doc: {meta.get('filename', 'N/A')}")
    print(f"   Content: {content[:300]}...")
    print(f"   Has Table: {meta.get('has_table', False)}")
    print()

# Search in chunks directly for the table content
print("=" * 80)
print("CHECKING ALL CHUNKS FOR TABLE KEYWORDS")
print("=" * 80)

# Get collection stats
try:
    collection = vector_store.collection
    count = collection.count()
    print(f"Total chunks in database: {count}\n")
    
    # Get a sample to check if table data exists
    all_data = collection.get(limit=200)
    
    lcd_chunks = []
    for i, content in enumerate(all_data['documents']):
        if 'lcd' in content.lower() or 'repair' in content.lower() and 'days' in content.lower():
            lcd_chunks.append({
                'id': all_data['ids'][i],
                'content': content,
                'metadata': all_data['metadatas'][i]
            })
    
    print(f"Found {len(lcd_chunks)} chunks mentioning LCD/Repair/Days:\n")
    for chunk in lcd_chunks[:5]:  # Show first 5
        print(f"ID: {chunk['id']}")
        print(f"File: {chunk['metadata'].get('filename', 'N/A')}")
        print(f"Page: {chunk['metadata'].get('page', 'N/A')}")
        print(f"Has Table: {chunk['metadata'].get('has_table', False)}")
        print(f"Content: {chunk['content'][:400]}")
        print("-" * 80)
        
except Exception as e:
    print(f"Error: {e}")
