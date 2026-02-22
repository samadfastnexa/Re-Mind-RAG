# RAG System - Complete Setup & Run Guide

## ✅ System Configuration Complete!

### 🗄️ Database: ChromaDB
- **Type**: Vector database for embeddings
- **Location**: `./data/chroma_db/` (persisted locally)
- **Configuration**: Fully managed via `.env` file

---

## 📋 Configuration Summary

### ✅ Backend (FastAPI)
**All configured via `.env` file:**
- ✅ **ChromaDB Path**: Configurable via `CHROMA_DB_PATH`
- ✅ **Port**: Configurable via `PORT` (default: 8000)
- ✅ **Host**: Configurable via `HOST` (default: 0.0.0.0)
- ✅ **CORS**: Configurable via `CORS_ORIGINS` (supports web + mobile)
- ✅ **OpenAI API Key**: Set via `OPENAI_API_KEY`

### ✅ Web App (Next.js)
- ✅ API URL configured in `.env.local`
- ✅ All components ready
- ✅ Responsive design

### ✅ Mobile App (React Native/Expo)
- ✅ API client configured
- ✅ All screens implemented
- ✅ Native navigation ready

---

## 🚀 Quick Start (3 Steps)

### Step 1: Install Dependencies

#### Backend:
```bash
cd f:\samad\chatobot\rag_system
pip install -r requirements.txt
```

#### Web App:
```bash
cd f:\samad\chatobot\rag-web
npm install
```

#### Mobile App:
```bash
cd f:\samad\chatobot\rag-mobile
npm install
```

---

### Step 2: Configure OpenAI API Key

Edit `f:\samad\chatobot\rag_system\.env`:
```env
OPENAI_API_KEY=sk-your-actual-api-key-here
```

---

### Step 3: Run All Applications

#### Terminal 1 - Backend API:
```bash
cd f:\samad\chatobot\rag_system
python -m app.main
```
✅ Backend running at: http://localhost:8000
📚 API Docs: http://localhost:8000/docs

#### Terminal 2 - Web App:
```bash
cd f:\samad\chatobot\rag-web
npm run dev
```
✅ Web app running at: http://localhost:3000

#### Terminal 3 - Mobile App:
```bash
cd f:\samad\chatobot\rag-mobile
npx expo start
```
✅ Scan QR code with Expo Go app on your phone

---

## 🔧 Environment Configuration Reference

### Backend `.env` File
```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-3.5-turbo
EMBEDDING_MODEL=text-embedding-3-small

# ChromaDB Configuration
CHROMA_DB_PATH=./data/chroma_db
COLLECTION_NAME=documents

# Upload Configuration
UPLOAD_DIR=./data/documents
MAX_FILE_SIZE_MB=50

# Server Configuration
HOST=0.0.0.0
PORT=8000

# CORS Configuration (comma-separated origins)
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,exp://,*
```

### Production CORS (Remove wildcard):
```env
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

---

## 📱 Features

### Web App Features:
- 💬 Real-time chat with AI
- 📄 Document upload (drag & drop)
- 📚 View all uploaded documents
- 🔍 Source citations in responses
- 📱 Responsive design (mobile-friendly)

### Mobile App Features:
- 💬 Native chat interface
- 📄 Document picker integration
- 📚 Document management
- 🎨 Native navigation
- 📱 Cross-platform (iOS & Android)

---

## 🗄️ Database Details

### ChromaDB
- **Type**: Embedded vector database
- **Storage**: SQLite-based persistence
- **Location**: `f:\samad\chatobot\rag_system\data\chroma_db\`
- **Embeddings**: OpenAI text-embedding-3-small
- **Auto-created**: Database initializes automatically on first run

**No separate database server needed!** ChromaDB runs embedded within your FastAPI application.

---

## 🔍 Health Check

Once running, verify everything works:
```bash
# Check backend health
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "version": "1.0.0",
  "chromadb_status": "healthy",
  "openai_configured": true
}
```

---

## 🎯 What's Next?

1. **Add your OpenAI API key** in `rag_system\.env`
2. **Install dependencies** (see Step 1 above)
3. **Run all three apps** (see Step 3 above)
4. **Upload a document** via web/mobile app
5. **Start chatting!**

---

## 📦 Updated Dependencies

### Backend (`requirements.txt`):
- FastAPI 0.109.0
- Uvicorn 0.27.0
- LangChain 0.1.0
- ChromaDB 0.4.22
- PyPDF2 3.0.1
- Python-dotenv 1.0.0
- Pydantic-settings 2.1.0

All organized and categorized for easy maintenance!

---

## ⚙️ Port Configuration

All ports configurable via `.env`:
- **Backend**: PORT=8000 (change if needed)
- **Web**: Uses Next.js default (3000)
- **Mobile**: Uses Expo default (19000+)

---

## 🎉 System Status: READY TO RUN!
