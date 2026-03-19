"""
Re-index the IT User Manual to properly capture Procedure #6.7.13 about theft reporting.
This script will delete the old index and create a new one with optimized chunking.
"""
import sys
sys.path.append('rag_system')

from app.services.document_processor import document_processor
from app.services.vector_store import vector_store

def reindex_it_user_manual():
    """Re-process and re-index the IT User Manual"""

    print("="*60)
    print("RE-INDEXING IT USER MANUAL")
    print("="*60)

    pdf_path = 'rag_system/data/documents/d557820c_(Revised) IT User Manual.pdf'
    filename = '(Revised) IT User Manual.pdf'

    # Step 1: Delete existing IT User Manual from vector store
    print("\n[1/3] Checking for existing IT User Manual in database...")
    docs = vector_store.list_documents()

    for doc in docs:
        if doc['filename'] == filename:
            print(f"  Found existing document: {doc['document_id']}")
            print(f"  Deleting {doc['chunks']} old chunks...")
            deleted = vector_store.delete_document(doc['document_id'])
            print(f"  ✓ Deleted {deleted} chunks")

    # Step 2: Process the document with current settings
    print(f"\n[2/3] Processing {filename}...")
    try:
        chunks_with_metadata, doc_id, num_pages = document_processor.process_document(
            pdf_path,
            filename
        )
        print(f"  ✓ Extracted {len(chunks_with_metadata)} chunks from {num_pages} pages")

        # Check if Page 35 content is in the chunks
        found_procedure = False
        for i, chunk in enumerate(chunks_with_metadata):
            if '6.7.13' in chunk['text']:
                print(f"\n  ✓ Found Procedure 6.7.13 in chunk {i}!")
                print(f"    Preview: {chunk['text'][:200]}...")
                found_procedure = True
                break

        if not found_procedure:
            print("\n  ⚠ WARNING: Procedure 6.7.13 not found in any chunk!")
            print("    The procedure might be split across multiple chunks.")

    except Exception as e:
        print(f"  ✗ Error processing document: {e}")
        return False

    # Step 3: Add to vector store
    print(f"\n[3/3] Adding {len(chunks_with_metadata)} chunks to vector database...")
    try:
        num_added = vector_store.add_documents(chunks_with_metadata, doc_id)
        print(f"  ✓ Successfully indexed {num_added} chunks")
        print(f"  Document ID: {doc_id}")
    except Exception as e:
        print(f"  ✗ Error adding to vector store: {e}")
        return False

    print("\n" + "="*60)
    print("RE-INDEXING COMPLETE!")
    print("="*60)
    print("\nTest the system by asking: 'What is the theft policy?'")
    print("Expected answer: Report loss/theft within 1 hour to Head of IT Networks and Internal Audit")

    return True

if __name__ == "__main__":
    reindex_it_user_manual()
