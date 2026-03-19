"""
Add missing Procedure #6.7.13 to the vector database.
This is a hotfix to add the theft reporting procedure that was skipped during SOP processing.
"""
import sys
sys.path.append('rag_system')

from app.services.vector_store import vector_store

# Procedure 6.7.13 content from page 35
PROCEDURE_6_7_13 = {
    "text": """Page: 35 | Section: Device Security Procedures

Step/Procedure No.: 6.7.13

Procedure:
Loss or theft of any device must be reported within 1 hour to Head of IT Networks and Internal Audit.

Performed by: Head of IT Networks

Control Owner: CTO

This is a critical security procedure to ensure:
- Immediate response to lost or stolen devices
- Quick activation of remote wipe capabilities
- Timely incident reporting for audit trails
- Prevention of unauthorized access to company data""",

    "metadata": {
        "document_id": None,  # Will be filled in
        "filename": "(Revised) IT User Manual.pdf",
        "chunk_index": 999,  # Special marker for manual addition
        "procedure_number": "6.7.13",
        "section": "Device Security",
        "page": 35,
        "manually_added": True,
        "keywords": ["theft", "loss", "device", "report", "1 hour", "IT Networks", "Internal Audit"]
    }
}

def add_procedure():
    """Add the missing procedure to the vector store."""

    print("="*60)
    print("ADDING MISSING PROCEDURE #6.7.13")
    print("="*60)

    # Get the existing IT User Manual document ID
    docs = vector_store.list_documents()
    it_manual = None

    for doc in docs:
        if doc['filename'] == '(Revised) IT User Manual.pdf':
            it_manual = doc
            break

    if not it_manual:
        print("\n❌ ERROR: IT User Manual not found in database!")
        print("   Please re-upload the IT User Manual first.")
        return False

    doc_id = it_manual['document_id']
    print(f"\n✓ Found IT User Manual: {doc_id}")
    print(f"  Current chunks: {it_manual['chunks']}")

    # Update metadata with document ID
    PROCEDURE_6_7_13['metadata']['document_id'] = doc_id
    PROCEDURE_6_7_13['metadata']['chunk_index'] = it_manual['chunks']  # Add as next chunk
    PROCEDURE_6_7_13['metadata']['total_chunks'] = it_manual['chunks'] + 1

    # Add to vector store
    print(f"\n📝 Adding Procedure #6.7.13...")
    try:
        num_added = vector_store.add_documents([PROCEDURE_6_7_13], doc_id)
        print(f"✓ Successfully added {num_added} chunk")
    except Exception as e:
        print(f"❌ Error adding procedure: {e}")
        return False

    # Verify it was added
    print(f"\n🔍 Verifying...")

    # Search for "theft policy"
    results = vector_store.similarity_search("theft policy", top_k=3)

    found = False
    for i, result in enumerate(results, 1):
        if '6.7.13' in result['content']:
            print(f"✓ Found in search results (rank #{i})!")
            found = True
            break

    if found:
        print("\n" + "="*60)
        print("SUCCESS! Procedure #6.7.13 has been added.")
        print("="*60)
        print("\nTest by asking: 'What is the theft policy?'")
        print("Expected: Report loss/theft within 1 hour to Head of IT Networks")
        return True
    else:
        print("\n⚠ Warning: Procedure was added but not found in top search results")
        print("   This might be a search ranking issue.")
        return False

if __name__ == "__main__":
    add_procedure()
