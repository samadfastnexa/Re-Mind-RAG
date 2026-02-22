# Quick Start Guide - Enhanced RAG System

## 🚀 Installation & Setup

### 1. Install Dependencies

```bash
# Navigate to backend
cd rag_system

# Install enhanced dependencies
pip install -r requirements.txt
```

**New packages being installed:**
- `rank-bm25` - BM25 keyword search
- `langchain-experimental` - Semantic chunking
- `sentence-transformers` - Cross-encoder reranking
- `numpy` - Numerical operations

### 2. Configure Environment

The system works with default settings, but you can customize in `.env`:

```bash
# Enhanced Features (all enabled by default)
ENABLE_HYBRID_SEARCH=True
ENABLE_RERANKING=True
USE_SEMANTIC_CHUNKING=True
ENABLE_SLIDING_WINDOW=True
ENABLE_CONVERSATION_HISTORY=True

# Fine-tuning (optional)
BM25_WEIGHT=0.3              # 30% keyword, 70% vector
HYBRID_TOP_K=20              # Candidates before reranking
RERANKER_TOP_K=6             # Final results after reranking
MAX_HISTORY_MESSAGES=10      # Conversation context size
```

### 3. Start the Backend

```bash
# From chatobot directory
cd rag_system
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**First Run Notes:**
- Reranker model (~90MB) downloads on first use
- Semantic chunking embeddings may take a moment to load
- All models cache locally for future use

### 4. Start the Frontend

```bash
# In a new terminal
cd rag-web
npm install  # If dependencies changed
npm run dev
```

Open: http://localhost:3000

---

## 📝 First-Time Usage

### Test the New Features:

1. **Upload a Document**
   - Go to Documents page
   - Upload a PDF or text file
   - New chunking strategy will automatically apply

2. **Try Different Answer Types**
   - Open Chat page
   - Click ⚙️ Settings
   - Select different answer types:
     - Summary - Quick overview
     - Detailed - Deep explanation
     - Bullet Points - Key points
     - Explain Simple - ELI5 style

3. **Test Conversation History**
   - Ask: "What is machine learning?"
   - Follow up: "What are its applications?"
   - The system remembers context!

4. **Rate Responses**
   - Click stars below assistant messages
   - Helps track quality over time

5. **Check Source Quality**
   - Expand sources below answers
   - See relevance scores (color-coded)
   - Green badges = highly relevant (>80%)

---

## 🔍 Verify Everything Works

### Check Feature Status:

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test enhanced query (with all features)
curl -X POST "http://localhost:8000/query" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "test question",
    "top_k": 6,
    "answer_type": "default"
  }'
```

**Look for in response:**
- `retrieval_metadata.hybrid_search_used: true`
- `retrieval_metadata.reranking_used: true`
- `sources[].relevance_score` - Should see scores

---

## 🎯 Quick Feature Examples

### Example 1: Compare Two Concepts
```json
{
  "question": "Compare React vs Vue",
  "answer_type": "compare",
  "top_k": 8
}
```

### Example 2: Get Summary
```json
{
  "question": "Summarize the main findings",
  "answer_type": "summary",
  "top_k": 10
}
```

### Example 3: Filter by Document
```json
{
  "question": "What is the revenue?",
  "filters": {"document_id": "doc_abc123"}
}
```

### Example 4: Conversation Follow-up
```javascript
// 1. Create session
const session = await api.createConversationSession();

// 2. First question
await api.queryDocuments({
    question: "What is AI?",
    session_id: session.session_id
});

// 3. Follow-up (remembers context)
await api.queryDocuments({
    question: "How does it work?",
    session_id: session.session_id
});
```

---

## ⚡ Performance Tips

### For Best Results:

1. **Document Size**
   - PDFs work great up to 50MB
   - Semantic chunking handles complex docs better
   
2. **Query Complexity**
   - Simple questions: `top_k: 4-6`
   - Complex questions: `top_k: 8-12`
   - Comparisons: `top_k: 10-15`

3. **Answer Types**
   - Default: Best for factual Q&A
   - Summary: For long documents
   - Detailed: For in-depth analysis
   - Bullet Points: For lists/features

4. **Conversation Sessions**
   - Create one session per chat thread
   - Clear sessions when switching topics
   - Sessions auto-expire after 60 min

---

## 🐛 Troubleshooting

### Reranker Not Loading?
```
Warning: Could not load reranker model
→ Check internet connection (downloads on first use)
→ System falls back to hybrid search without reranking
→ Still works, just slightly less accurate
```

### Semantic Chunking Errors?
```
Semantic chunking failed, using recursive splitter
→ This is normal for some document types
→ System automatically falls back
→ Results still good with standard chunking
```

### Slow First Query?
```
→ First query loads models into memory
→ Subsequent queries much faster
→ Models stay cached
```

### Session Expired?
```
→ Sessions timeout after 60 minutes
→ Simply create a new session
→ Old history is cleared
```

---

## 🎓 Learn More

- **Feature Guide**: See `ENHANCED_RAG_FEATURES.md` for detailed documentation
- **API Docs**: Visit http://localhost:8000/docs for interactive API testing
- **Configuration**: Check `rag_system/app/config.py` for all settings

---

## ✅ Success Checklist

After setup, you should have:

- [x] Backend running on port 8000
- [x] Frontend running on port 3000
- [x] New dependencies installed
- [x] Can upload documents
- [x] Can query with different answer types
- [x] Can see enhanced source citations
- [x] Can rate responses
- [x] Conversation history works

---

## 🎉 You're Ready!

Your RAG system is now production-grade with:
- 🔍 Smarter retrieval (hybrid + reranking)
- 💬 Conversation memory
- 🎨 Multiple answer formats
- ⭐ User feedback
- 📊 Enhanced transparency

Happy querying! 🚀
