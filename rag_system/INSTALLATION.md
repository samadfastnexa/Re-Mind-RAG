# Installation Guide

## ✅ **Quick Install**

### Option 1: Standard Installation (Recommended)

```powershell
cd F:\samad\chatobot\rag_system
pip install -r requirements.txt
```

### Option 2: Using Install Script (If Option 1 Fails)

```powershell
cd F:\samad\chatobot\rag_system
.\install-dependencies.ps1
```

### Option 3: Minimal Installation (Fastest)

```powershell
cd F:\samad\chatobot\rag_system
pip install -r requirements-minimal.txt
```

---

## 🔧 **Troubleshooting Installation Issues**

### Issue: "No module named 'fastapi'"

**Solution:**
```powershell
pip install fastapi uvicorn
```

### Issue: "langchain-experimental fails to install"

**Solution:** Comment out that line in requirements.txt or use requirements-minimal.txt

### Issue: "Dependency resolution takes forever"

**Solution:** Use the step-by-step installation script:
```powershell
.\install-dependencies.ps1
```

### Issue: "pip is not recognized"

**Solution:** Use python -m pip:
```powershell
python -m pip install -r requirements.txt
```

---

## 🚀 **Starting the Server**

After installation:

```powershell
# Make sure you're in rag_system directory
cd F:\samad\chatobot\rag_system

# Start the server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Access:**
- API Docs: http://localhost:8000/docs
- API: http://localhost:8000

---

## 📦 **What Gets Installed**

### Core Components:
- **FastAPI** - Web framework
- **LangChain** - LLM orchestration
- **ChromaDB** - Vector database
- **Sentence Transformers** - Embeddings
- **rank-bm25** - Keyword search

### Enhanced Features:
- **Hybrid Search** - Vector + Keyword
- **Reranking** - Cross-encoder models
- **Conversation History** - Session management
- **Multiple Answer Types** - Flexible responses

---

## ⚡ **Speed Tips**

1. Use a virtual environment:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

2. Install minimal first, add features later:
```powershell
pip install -r requirements-minimal.txt
# Test if server starts
# Then install additional packages as needed
```

3. Use cached packages:
```powershell
pip install --cache-dir ./pip_cache -r requirements.txt
```

---

## 📝 **Verify Installation**

```powershell
python -c "import fastapi, langchain, chromadb; print('✅ All core packages OK')"
```

If this prints "✅ All core packages OK", you're ready to start the server!
