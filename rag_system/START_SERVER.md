# Quick Start Guide - RAG System

## ✅ Installation Complete!

All dependencies have been successfully installed.

## 🚀 How to Run the Server

### Step 1: Navigate to the project directory
```bash
cd f:\samad\chatobot\rag_system
```

### Step 2: Activate the virtual environment
```bash
.\venv\Scripts\activate
```

### Step 3: Add your OpenAI API Key

Edit the `.env` file and replace `your_openai_api_key_here` with your actual OpenAI API key:

```env
OPENAI_API_KEY=sk-your-actual-api-key-here
```

Get your API key from: https://platform.openai.com/api-keys

### Step 4: Start the server
```bash
python -m uvicorn app.main:app --reload
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
cd f:\samad\chatobot\rag_system; f:\samad\chatobot\rag_system\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

Or simply:
```bash
uvicorn app.main:app --reload
```

The server will start at: **http://localhost:8000**

## 📚 Access the API

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **API Root**: http://localhost:8000

## 🧪 Test the System

1. Open http://localhost:8000/docs in your browser
2. Click on **POST /upload** endpoint
3. Click "Try it out"
4. Upload a PDF or text file
5. Click "Execute"
6. Copy the `document_id` from the response
7. Go to **POST /query** endpoint
8. Enter your question and click "Execute"

## 📝 Example API Calls

### Upload a document
```bash
curl -X POST "http://localhost:8000/upload" -F "file=@document.pdf"
```

### Query the document
```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this document about?", "top_k": 4}'
```

## ⚠️ Troubleshooting

**If you get "uvicorn not found":**
- Make sure you activated the virtual environment
- Run: `.\venv\Scripts\activate`

**If you get OpenAI API errors:**
- Check that you've added your API key to `.env`
- Verify the API key is valid

**If you get import errors:**
- Reinstall dependencies: `pip install -r requirements.txt`

---

**You're all set! 🎉**
