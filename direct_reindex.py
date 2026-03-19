"""
Direct re-index script — no HTTP server required.
Deletes all duplicate IT Department Manual entries and re-indexes from disk.

Run from the project root with the .venv active:
    python direct_reindex.py
"""
import sys
import glob
import os

sys.path.insert(0, 'rag_system')

# ── Imports (uses .venv packages) ────────────────────────────────────────────
print("Loading RAG system modules...")
from app.services.vector_store import vector_store
from app.services.document_processor import document_processor

# ── Step 1: Find all IT Department Manual entries ────────────────────────────
print("\n[1/3] Scanning vector store for IT Department Manual copies...")
all_docs = vector_store.list_documents()
print("      Total documents in store: %d" % len(all_docs))

manual_docs = [d for d in all_docs if "IT Department Manual" in d.get("filename", "")]
print("      IT Department Manual copies found: %d" % len(manual_docs))
for d in manual_docs:
    print("        - %-38s | %3d chunks | %s" % (
        d["document_id"], d.get("chunks", 0), d.get("filename", "?")
    ))

# ── Step 2: Delete all old copies ────────────────────────────────────────────
print("\n[2/3] Deleting all old copies...")
for doc in manual_docs:
    deleted = vector_store.delete_document(doc["document_id"])
    print("      Deleted %-38s (%d chunks removed)" % (doc["document_id"], deleted))

# ── Step 3: Re-index the newest local PDF ────────────────────────────────────
pdf_files = glob.glob("rag_system/data/documents/*IT Department Manual.pdf")
if not pdf_files:
    print("\nERROR: No PDF matching '*IT Department Manual.pdf' found in rag_system/data/documents/")
    sys.exit(1)

pdf_files.sort(key=os.path.getmtime, reverse=True)
pdf_path = pdf_files[0]
filename = "(Revised) IT Department Manual.pdf"
print("\n[3/3] Re-indexing: %s" % pdf_path)

chunks_with_meta, doc_id, num_pages = document_processor.process_document(pdf_path, filename)
print("      Extracted %d chunks from %d pages" % (len(chunks_with_meta), num_pages))

# Quick sanity check: 7.2.10 must be present
found_710 = any("7.2.10" in c["text"] or "7.2.10" in c["metadata"].get("procedure_no", "")
                for c in chunks_with_meta)
print("      Procedure 7.2.10 present: %s" % ("YES" if found_710 else "NO -- something is wrong!"))

# Find and show the 7.2.10 chunk
for c in chunks_with_meta:
    if "7.2.10" in c["metadata"].get("procedure_no", ""):
        print("\n      7.2.10 preview:")
        print("      " + c["text"][:400].replace("\n", "\n      "))
        break

# Add to vector store
num_added = vector_store.add_documents(chunks_with_meta, doc_id)
print("\n      Indexed %d chunks (doc_id: %s)" % (num_added, doc_id))

print("\nDone! Restart the server so the new index is served with a fresh query cache.")
print("Then ask: 'what is the theft policy?' — should now answer with Procedure 7.2.10.")
