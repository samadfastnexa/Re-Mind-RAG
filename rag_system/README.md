# RAG System - Retrieval-Augmented Generation

A production-ready RAG (Retrieval-Augmented Generation) system built with **ChromaDB**, **OpenAI GPT-3.5-turbo**, and **LangChain**. Upload PDF and text documents, then ask questions and get AI-powered answers with source citations.

## 🚀 Features

- ✅ **Document Upload**: Support for PDF and text files (up to 100 pages)
- ✅ **Smart Chunking**: Intelligent text splitting for optimal retrieval
- ✅ **Vector Search**: ChromaDB for fast similarity search
- ✅ **AI-Powered Answers**: OpenAI GPT-3.5-turbo for natural language responses
- ✅ **Source Citations**: Answers include references to source documents
- ✅ **REST API**: FastAPI with automatic Swagger documentation
- ✅ **Document Management**: List and delete uploaded documents

## 📋 Prerequisites

- Python 3.10 or higher
- OpenAI API key ([Get one here](https://platform.openai.com/api-keys))

## 🛠️ Installation

### 1. Clone or Navigate to Project

```bash
cd f:\samad\chatobot\rag_system
```

### 2. Create Virtual Environment

```bash
python -m venv venv
```

### 3. Activate Virtual Environment

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```env
OPENAI_API_KEY=sk-your-actual-api-key-here
OPENAI_MODEL=gpt-3.5-turbo
EMBEDDING_MODEL=text-embedding-3-small
```

## 🚀 Running the Server

Start the FastAPI server:

```bash
uvicorn app.main:app --reload
```

The server will start at: **http://localhost:8000**

## 📚 API Documentation

Once the server is running, access the interactive Swagger UI:

**Swagger UI**: http://localhost:8000/docs

**ReDoc**: http://localhost:8000/redoc

## 🔧 API Endpoints

### 1. Upload Document

**POST** `/upload`

Upload a PDF or text file for processing.

```bash
curl -X POST "http://localhost:8000/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your_document.pdf"
```

**Response:**
```json
{
  "success": true,
  "message": "Document uploaded and processed successfully",
  "document_id": "doc_abc123",
  "filename": "your_document.pdf",
  "pages": 25,
  "chunks": 42
}
```

### 2. Query Documents

**POST** `/query`

Ask questions about your uploaded documents.

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the main topic of the document?",
    "top_k": 4
  }'
```

**Response:**
```json
{
  "question": "What is the main topic of the document?",
  "answer": "The document discusses...",
  "sources": [
    {
      "document": "your_document.pdf",
      "chunk": 1,
      "content": "Relevant excerpt...",
      "relevance_score": 0.92
    }
  ]
}
```

### 3. List Documents

**GET** `/documents`

Get a list of all uploaded documents.

```bash
curl -X GET "http://localhost:8000/documents"
```

### 4. Delete Document

**DELETE** `/documents/{document_id}`

Delete a document and all its chunks.

```bash
curl -X DELETE "http://localhost:8000/documents/doc_abc123"
```

### 5. Health Check

**GET** `/health`

Check system health and configuration.

```bash
curl -X GET "http://localhost:8000/health"
```

### 6. Statistics

**GET** `/stats`

Get system statistics.

```bash
curl -X GET "http://localhost:8000/stats"
```

## 📁 Project Structure

```
rag_system/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── models.py            # Pydantic models
│   └── services/
│       ├── __init__.py
│       ├── document_processor.py  # PDF/text processing
│       ├── vector_store.py        # ChromaDB operations
│       └── rag_chain.py           # LangChain RAG logic
├── data/
│   ├── documents/           # Uploaded documents
│   └── chroma_db/           # ChromaDB storage
├── requirements.txt
├── .env.example
├── .env
└── README.md
```

## 🔑 Configuration Options

Edit `.env` to customize:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key | Required |
| `OPENAI_MODEL` | GPT model to use | `gpt-3.5-turbo` |
| `EMBEDDING_MODEL` | Embedding model | `text-embedding-3-small` |
| `CHROMA_DB_PATH` | ChromaDB storage path | `./data/chroma_db` |
| `UPLOAD_DIR` | Document upload directory | `./data/documents` |
| `MAX_FILE_SIZE_MB` | Max upload size | `50` |
| `CHUNK_SIZE` | Text chunk size | `1000` |
| `CHUNK_OVERLAP` | Chunk overlap | `200` |

## 💡 Usage Examples

### Using Swagger UI (Recommended)

1. Go to http://localhost:8000/docs
2. Click on **POST /upload**
3. Click "Try it out"
4. Upload your PDF or text file
5. Click "Execute"
6. Copy the `document_id` from the response
7. Go to **POST /query**
8. Enter your question and click "Execute"

### Using Python

```python
import requests

# Upload document
with open("document.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/upload",
        files={"file": f}
    )
    doc_info = response.json()
    print(f"Uploaded: {doc_info['document_id']}")

# Query document
response = requests.post(
    "http://localhost:8000/query",
    json={
        "question": "What is this document about?",
        "top_k": 4
    }
)
result = response.json()
print(f"Answer: {result['answer']}")
print(f"Sources: {len(result['sources'])} chunks")
```

## 🐛 Troubleshooting

### "OpenAI API key not configured"

Make sure you've created a `.env` file with your actual OpenAI API key.

### "Module not found" errors

Ensure you've activated the virtual environment and installed dependencies:
```bash
venv\Scripts\activate
pip install -r requirements.txt
```

### ChromaDB errors

Delete the ChromaDB directory and restart:
```bash
rm -rf data/chroma_db
```

## 📊 Performance

- **Document Processing**: ~2-5 seconds for a 50-page PDF
- **Query Response**: ~1-3 seconds depending on document size
- **Supported Volume**: Up to 100 pages per document, unlimited documents

## 🔒 Security Notes

- Never commit your `.env` file to version control
- Keep your OpenAI API key secure
- Consider rate limiting for production use
- Validate file uploads in production environments

## 📝 License

This project is open source and available for personal and commercial use.

## 🤝 Support

For issues or questions:
1. Check the Swagger documentation at `/docs`
2. Review the troubleshooting section
3. Check OpenAI API status

## 🚀 Next Steps

- Add authentication and user management
- Implement conversation history
- Add support for more file types (DOCX, HTML)
- Deploy to cloud (AWS, GCP, Azure)
- Add frontend UI (React, Vue, etc.)

---

**Built with ❤️ using ChromaDB, OpenAI, and LangChain**
