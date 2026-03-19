# Advanced Document Processing and Intelligent Chunking

## Overview

The RAG system now features **intelligent document processing** with advanced chunking that preserves document structure, tables, images, and page numbers. This dramatically improves the quality of document understanding and answer accuracy.

## Features

### ✨ Key Improvements

1. **Intelligent Chunking**
   - Respects document structure (headings, sections, paragraphs)
   - Keeps related content together
   - No more broken table of contents or mid-sentence splits
   - Context-aware splitting that understands semantic boundaries

2. **Table Extraction & Preservation**
   - Tables are extracted intact
   - Converted to markdown format for better LLM understanding
   - Table data preserved with page numbers
   - Each table gets its own chunk to prevent fragmentation

3. **Image Extraction**
   - Images are automatically extracted from PDFs
   - Saved as separate PNG files
   - Referenced in nearby text chunks
   - Image metadata includes page numbers and bounding boxes
   - Base64 encoding available for API responses

4. **Page Number Tracking**
   - Every chunk includes accurate page numbers
   - Page ranges for chunks spanning multiple pages
   - LLM instructed to cite page numbers in answers
   - Easy reference back to source documents

5. **Enhanced Metadata**
   - Document structure type (heading, paragraph, list, table)
   - Chunk type (text, table)
   - Page information (single page or range)
   - Related images
   - Table data in structured format
   - Bounding boxes for tables and images

## Configuration

### Environment Variables (.env)

Add these settings to your `.env` file:

```bash
# Advanced Document Processing
USE_ADVANCED_PROCESSING=true    # Enable advanced processor
EXTRACT_TABLES=true             # Extract and preserve tables
EXTRACT_IMAGES=true             # Extract images from documents
SAVE_EXTRACTED_IMAGES=true     # Save images to disk

# Chunking Configuration
CHUNK_SIZE=600                  # Target chunk size (characters)
CHUNK_OVERLAP=150               # Overlap between chunks

# Search & Retrieval
RETRIEVAL_TOP_K=8              # Number of chunks to retrieve
ENABLE_HYBRID_SEARCH=true      # Combine vector + keyword search
ENABLE_RERANKING=true          # Rerank results for relevance
```

### Configuration Options Explained

**USE_ADVANCED_PROCESSING**
- `true`: Uses pdfplumber with intelligent structure-aware chunking
- `false`: Uses basic PyPDF2 with simple character-based chunking
- **Recommended**: `true` for production

**EXTRACT_TABLES**
- Extracts tables and keeps them intact
- Tables are converted to markdown format
- Each table gets its own dedicated chunk

**EXTRACT_IMAGES**
- Extracts images from PDFs
- Images are referenced in related text chunks
- Useful for documents with diagrams, charts, screenshots

**SAVE_EXTRACTED_IMAGES**
- Saves extracted images to `data/documents/images/`
- Files named: `{document_id}_page{N}_img{N}.png`
- Images can be retrieved via API for display

**CHUNK_SIZE & CHUNK_OVERLAP**
- Smaller chunks (400-800) work better for precise answers
- Larger overlap (150-200) preserves more context
- Tables and long sections may exceed chunk_size (intentional)

## How It Works

### Document Processing Pipeline

```
PDF Document
    ↓
1. Extract Elements
   - Text sections (grouped by paragraph/heading)
   - Tables (with structure preserved)
   - Images (with bounding boxes)
    ↓
2. Structure Analysis
   - Detect headings (ALL CAPS sections)
   - Identify list items (numbered, bulleted)
   - Group related paragraphs
    ↓
3. Intelligent Chunking
   - Tables → Dedicated chunks (kept intact)
   - Headings → Grouped with following content
   - Long sections → Split at semantic boundaries
   - Images → Referenced in nearby text chunks
    ↓
4. Metadata Enrichment
   - Add page numbers
   - Add chunk type (text/table)
   - Link related images
   - Include position info
    ↓
5. Vector Storage
   - Generate embeddings
   - Store with full metadata
   - Index for hybrid search
```

### Chunking Strategy

#### Old Approach (Basic)
```
❌ Problem: Unintelligent splitting

"5 4.2. RESPONSIBILITIES........."  (Chunk 4)
"..........8 6.3. PLANNING PROCEDURES"  (Chunk 6)

- Breaks table of contents
- Splits headings from content
- No page numbers
- Tables get fragmented
```

#### New Approach (Intelligent)
```
✅ Solution: Structure-aware chunking

**Table (Page 5)**
| Section | Description | Page |
|---------|-------------|------|
| 4.2 | RESPONSIBILITIES | 5 |
| 6.3 | PLANNING PROCEDURES | 8 |

- Complete table intact
- Page number preserved
- Markdown formatted
- Dedicated chunk
```

### Example Chunks

#### Text Chunk with Page Info
```json
{
  "text": "SAFETY PROCEDURES\n\nAll personnel must follow safety guidelines...",
  "metadata": {
    "document_id": "doc_abc123",
    "filename": "safety_manual.pdf",
    "chunk_index": 5,
    "chunk_type": "text",
    "page": 12,
    "pages": [12],
    "has_table": false,
    "has_images": false
  }
}
```

#### Table Chunk
```json
{
  "text": "**Table (Page 8)**\n| Item | Quantity | Price |\n|------|----------|-------|...",
  "metadata": {
    "document_id": "doc_abc123",
    "filename": "inventory.pdf",
    "chunk_index": 10,
    "chunk_type": "table",
    "page": 8,
    "has_table": true,
    "table_data": {
      "type": "table",
      "page": 8,
      "data": [["Item", "Quantity", "Price"], [...]]
    }
  }
}
```

#### Chunk with Images
```json
{
  "text": "System architecture diagram shows three main components...",
  "metadata": {
    "document_id": "doc_abc123",
    "filename": "architecture.pdf",
    "chunk_index": 3,
    "page_range": "3-4",
    "pages": [3, 4],
    "has_images": true,
    "related_images": [
      {
        "type": "image",
        "page": 3,
        "index": 0,
        "base64": "iVBORw0KGgo..."
      }
    ]
  }
}
```

## Installation

### 1. Update Dependencies

```powershell
cd rag_system
pip install -r requirements.txt
```

New dependencies include:
- `pdfplumber` - Advanced PDF parsing with layout awareness
- `unstructured` - Document structure analysis
- `pdf2image` - Image extraction from PDFs
- `pillow` - Image processing
- `pandas` - Table handling
- `tabulate` - Table formatting

### 2. Update Configuration

Edit your `.env` file:

```bash
# Enable advanced processing
USE_ADVANCED_PROCESSING=true
EXTRACT_TABLES=true
EXTRACT_IMAGES=true
SAVE_EXTRACTED_IMAGES=true
```

### 3. Restart Server

```powershell
# Stop existing server (Ctrl+C)
# Start with new configuration
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Re-upload Documents

For best results, re-upload your existing documents to take advantage of the new chunking:

```bash
# Via API
curl -X POST "http://localhost:8000/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.pdf"
```

## API Response Structure

### Query Response with Enhanced Sources

```json
{
  "success": true,
  "answer": "According to page 12, the safety procedures require...",
  "sources": [
    {
      "source_id": 1,
      "document": "safety_manual.pdf",
      "page": 12,
      "chunk": 5,
      "has_table": false,
      "has_images": false,
      "content": "SAFETY PROCEDURES...",
      "relevance_score": 0.95
    },
    {
      "source_id": 2,
      "document": "inventory.pdf",
      "page": 8,
      "chunk": 10,
      "has_table": true,
      "table_data": {
        "type": "table",
        "page": 8,
        "markdown": "| Item | Quantity |..."
      },
      "content": "**Table (Page 8)**...",
      "relevance_score": 0.87
    }
  ],
  "conversation_session": "session_xyz"
}
```

## Benefits

### For Users

✅ **Accurate Page Citations**
- "According to page 5..."
- Easy to verify information in source documents

✅ **Complete Table Data**
- No more fragmented tables
- Full table context preserved
- Markdown formatting readable by LLM

✅ **Image Awareness**
- System knows when images are present
- Can reference diagrams, charts, screenshots
- Images available for retrieval

✅ **Better Answers**
- Context-aware chunks mean better understanding
- Headings grouped with content
- Related information stays together

### For Developers

✅ **Rich Metadata**
- Comprehensive chunk information
- Easy filtering by page, type, document
- Image and table data structures

✅ **Flexible Processing**
- Can toggle advanced features on/off
- Backward compatible with basic processing
- Configurable chunk sizes and overlaps

✅ **Extensible**
- Clean separation of concerns
- Easy to add new element types
- Modular processor design

## Performance Considerations

### Processing Time
- Advanced processing takes ~2-3x longer than basic
- Tradeoff: Much better quality chunks
- Consider async processing for large documents

### Storage
- Images increase storage requirements
- Each image ~50-500KB depending on size
- Tables stored as text (minimal overhead)

### Memory
- pdfplumber uses more memory than PyPDF2
- Recommend 4GB+ RAM for production
- Consider batch processing for very large PDFs

### Embeddings
- More structured chunks = better embeddings
- Tables in markdown = LLM can understand structure
- Page-specific chunks = more precise retrieval

## Troubleshooting

### Images Not Extracting
```bash
# Install system dependencies (Windows)
# pdf2image requires poppler
# Download from: https://github.com/oschwartz10612/poppler-windows
# Add to PATH

# Test OCR (optional)
pip install pytesseract
# Download Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
```

### Tables Not Detected
- pdfplumber works best with "true" PDF tables
- Scanned PDFs need OCR first
- Complex nested tables may not extract perfectly

### Memory Issues
```bash
# Reduce chunk size
CHUNK_SIZE=400

# Disable image saving
SAVE_EXTRACTED_IMAGES=false

# Process fewer chunks at once
RETRIEVAL_TOP_K=5
```

### Slow Processing
```bash
# Disable advanced processing for text files
# (Only use for PDFs)

# Reduce image resolution in code
# advanced_document_processor.py: resolution=150 → resolution=100

# Disable semantic chunking
USE_SEMANTIC_CHUNKING=false
```

## Migration Guide

### From Old to New Chunking

1. **Backup existing data**
   ```powershell
   Copy-Item data/chroma_db data/chroma_db_backup -Recurse
   ```

2. **Update configuration**
   - Set `USE_ADVANCED_PROCESSING=true`

3. **Clear old chunks** (optional)
   ```powershell
   # Delete and rebuild
   Remove-Item data/chroma_db -Recurse
   ```

4. **Re-upload documents**
   - Use existing upload endpoints
   - Documents will be processed with new chunking

5. **Verify improvements**
   - Check chunk structure in database
   - Test queries with page number citations
   - Verify table extraction

## Best Practices

### Document Preparation
- Use native PDFs (not scanned) for best results
- Ensure tables are "true" PDF tables
- High-quality images extract better

### Chunking Configuration
- Start with defaults (600/150)
- Adjust based on your document types
- Technical docs: smaller chunks (400-600)
- Narrative docs: larger chunks (800-1200)

### Search Settings
- Enable hybrid search for better table retrieval
- Use reranking for highest quality
- Increase top_k (8-10) for comprehensive answers

### Testing
- Always test with representative documents
- Verify table extraction quality
- Check page number accuracy
- Review image extraction results

## Examples

### Query with Page Citations

**Question**: "What are the safety requirements?"

**Answer**: "According to page 12 of the safety manual, the following safety requirements must be met:

1. **Personal Protective Equipment** (page 12)
   - Hard hats in construction zones
   - Safety glasses required at all times

2. **Emergency Procedures** (pages 13-14)
   - Emergency exits marked clearly
   - Fire extinguishers every 50 feet

The safety requirements table on page 15 provides a complete checklist."

### Table-Aware Response

**Question**: "Show me the inventory levels"

**Answer**: "Based on the inventory table from page 8:

| Item | Current Stock | Reorder Level |
|------|---------------|---------------|
| Item A | 150 | 100 |
| Item B | 45 | 50 |
| Item C | 200 | 150 |

Item B is below reorder level and needs restocking (page 8)."

## Future Enhancements

- [ ] OCR for scanned documents
- [ ] Multi-column layout detection
- [ ] Equation/formula extraction
- [ ] Cross-reference resolution
- [ ] Section hierarchy preservation
- [ ] Chart/graph data extraction
- [ ] Footnote linking
- [ ] Header/footer removal

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review configuration settings
3. Test with sample documents
4. Check logs for processing errors

---

**Last Updated**: March 4, 2026
**Version**: 2.0
**Status**: ✅ Production Ready
