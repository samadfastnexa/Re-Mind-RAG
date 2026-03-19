# SOP Document Processing - Fix Guide

## What Was Wrong

Your IT Department Manual was being chunked with **fixed-size chunks (658 characters)**, which broke procedures awkwardly:

```
❌ BAD (Old way - fixed-size chunking):
Chunk 1: "Step/Procedure No.: 6.3.1 Performed By: Head of IT Networks Procedure: The Annual Information Technology Plan will be prepared by the CTO, CIO, CISO. The plan shall include a mandatory..."

Chunk 2: "...Information Security Impact Assessment section identifying security risks, required controls, and alignment with the ISMS risk treatment plan. Control Objective: Ensure the Information..."
```

The problem: **Related fields were split across multiple chunks**, making retrieval less accurate.

## What I Fixed

I created a **specialized SOP Processor** that:

1. ✅ **Detects SOP/procedure documents** automatically
2. ✅ **Chunks by procedure units** instead of character count
3. ✅ **Keeps related fields together**:
   - Step/Procedure No.
   - Procedure description
   - Control Objective
   - Control Owner
   - Communication Channel
   - Reference Document

```
✅ GOOD (New way - procedure-based chunking):
Chunk 1:
[Document: FCL|SOP|ITD|01 | Version: 1.00]
Page: 13 | Section: Physical Security of IT Assets & IT Infrastructure

Step/Procedure No.: 6.3.1
Performed By: Head of IT Networks

Procedure:
The Annual Information Technology Plan will be prepared by the CTO, CIO, CISO. 
The plan shall include a mandatory "Information Security Impact Assessment" 
section identifying security risks, required controls, and alignment with 
the ISMS risk treatment plan.

Control Objective:
Ensure the Information Technology Plan is prepared.

Control Owner: Respective C Officers
Communication Channel: Email
Reference Document: ITD-P1- P05
```

## Features Added

### 1. **Automatic SOP Detection**
The system now automatically detects documents with:
- Procedure numbers (6.3.1, 7.1.2, etc.)
- Control Objectives
- Control Owners
- Standard Operating Procedure patterns

### 2. **Procedure-Based Chunking**
Each procedure becomes one chunk, keeping all related information together.

### 3. **Enhanced Metadata**
Every chunk now includes:
- `procedure_no`: "6.3.1"
- `control_owner`: "CSO"
- `section_id`: "Physical Security of IT Assets"
- `page`: 13
- `group`: "IT Planning & Strategy" (auto-categorized)
- `communication_channel`: "Email"
- `reference_document`: "ITD-P1- P05"

### 4. **Smart Categorization**
Procedures are automatically categorized into groups:
- IT Planning & Strategy
- Physical Security
- Asset Management
- User Management
- Network Security
- Access Control
- Backup & Recovery
- Change Management
- Incident Management
- Compliance & Audit
- Data Protection
- Server Management
- Service Level Agreement

## How to Re-Process Your Document

### Option 1: Using the Web Interface

1. **Delete the old document:**
   - Go to http://localhost:3000/documents
   - Find "(Revised) IT Department Manual.pdf"
   - Click Delete

2. **Re-upload the document:**
   - Go to http://localhost:3000/upload
   - Upload the PDF again
   - The system will automatically detect it's an SOP and use procedure-based chunking
   - You'll see: "🔍 Detected SOP/Procedure document"

### Option 2: Using the API

Run the helper script (see below) or use curl:

```bash
# Delete old document
curl -X DELETE "http://localhost:8001/documents/doc_dedad5156804" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Upload with auto-detection (will use SOP processing)
curl -X POST "http://localhost:8001/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@path/to/(Revised) IT Department Manual.pdf"
```

### Option 3: Force Processing Mode

If you want to explicitly control processing:

```bash
# Force SOP/hybrid processing
curl -X POST "http://localhost:8001/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@path/to/document.pdf" \
  -F "processing_mode=auto"  # auto, text, structured, or hybrid
```

## Verify the Improvement

After re-uploading, test with your query:

```
Query: "What is the process for purchasing new hardware?"
```

**Before (bad chunks):**
- Sources reference truncated text
- Missing context about approval workflow
- Fragmented procedure steps

**After (procedure chunks):**
- Complete procedure in one source
- All steps clearly listed
- Control owners and references included
- Better answers with full context

## Check Chunk Quality

You can inspect chunks in the documents view to verify they now contain complete procedures instead of arbitrary text fragments.

Look for chunk metadata like:
- ✅ `procedure_no`: "6.3.1"
- ✅ `section_id`: "Physical Security"
- ✅ `control_owner`: "CSO"
- ✅ Complete procedure text in one chunk

## Configuration

The SOP processor is enabled by default. To disable it:

Edit `rag_system/.env`:
```bash
USE_SOP_PROCESSING=false  # Disable automatic SOP detection
```

Or in `app/config.py`:
```python
use_sop_processing: bool = False
```

## Supported Document Types

The SOP processor automatically detects and handles:
- ✅ Standard Operating Procedures (SOPs)
- ✅ Policy Manuals
- ✅ IT Department Manuals
- ✅ Compliance Documents
- ✅ Procedure Handbooks
- ✅ Process Documentation
- ✅ Control Frameworks (ISO 27001, SOC 2, etc.)

## Technical Details

### Detection Criteria
A document is classified as SOP if it contains 3+ of these patterns:
- Procedure numbers (Step 6.3.1, Procedure No.: 7.1.2)
- Control Objectives
- Control Owners
- Reference Documents
- Communication Channels
- SOP/Policy Manual keywords

### Chunking Strategy
1. Extract text with page markers
2. Detect procedure boundaries (Step No., Procedure No.)
3. Extract structured fields from each procedure
4. Create one chunk per procedure
5. Add rich metadata for filtering

### Fallback Behavior
If SOP detection fails or is disabled:
- Falls back to standard advanced processing
- Uses RecursiveCharacterTextSplitter (1200 chars)
- Still extracts tables and images
- Applies smart_text_parser for metadata enhancement

## Troubleshooting

### "My document isn't being detected as SOP"
Check that your document contains the required patterns. You can manually force SOP processing:

```python
# In Python
from app.services.sop_processor import sop_processor
chunks, doc_id, num_pages = sop_processor.process_pdf(
    "path/to/document.pdf",
    "document.pdf",
    None  # Auto-generate ID
)
```

### "I want to customize the chunking"
Edit `app/services/sop_processor.py`:
- Modify `procedure_boundary_patterns` to add new boundary markers
- Adjust `field_patterns` to extract additional fields
- Update `_categorize_procedure` to add new categories

### "Chunks are still too large/small"
For SOP documents, chunk size is determined by procedure length, not character count. Each procedure is kept intact. If you need finer granularity, you can split large procedures by sub-steps.

## Next Steps

1. ✅ **Re-upload your IT Department Manual** to get procedure-based chunks
2. ✅ **Test queries** to verify improved accuracy
3. ✅ **Upload other SOP documents** - they'll be auto-detected
4. ✅ **Review chunk quality** in the documents view

The system will now automatically handle SOP documents correctly, keeping procedures intact and adding rich metadata for better retrieval!
