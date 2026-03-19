# Re-Mind RAG - Intelligent Document Q&A System

A full-stack **Retrieval-Augmented Generation (RAG)** system with authentication, enabling users to upload documents and ask AI-powered questions. Built with FastAPI, Next.js, and React Native.

## 🌟 Overview

Re-Mind RAG is a complete document intelligence platform that allows users to:
- 📄 Upload PDF and text documents
- 🤖 Ask questions and get AI-powered answers with source citations
- 🔐 Secure user authentication and authorization
- 💻 Access via web browser or mobile app
- 🆓 Use FREE local AI models (Ollama) or paid OpenAI API
- 🌐 Connect to local or remote Ollama servers for distributed AI
- 🚀 Production-ready with FastAPI backend and modern frontends

## 🏗️ Project Structure

This is a monorepo containing three main components:

```
chatobot/
├── rag_system/          # Backend API (FastAPI + ChromaDB + LangChain)
│   ├── app/
│   ├── data/
│   └── README.md        # Detailed backend documentation
├── rag-web/             # Web Frontend (Next.js + React)
│   ├── app/
│   ├── components/
│   └── README.md
├── rag-mobile/          # Mobile App (React Native + Expo)
│   ├── app/
│   ├── services/
│   └── README.md
└── README.md            # This file
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+** (for backend)
- **Node.js 18+** (for web and mobile)
- **Choose ONE LLM Provider:**
  - **Ollama** (FREE - Local/Remote AI models) - [Download](https://ollama.ai) OR use remote server
  - **OpenAI API Key** (Paid - Cloud API) - [Get here](https://platform.openai.com/api-keys)

### 1️⃣ Backend Setup (FastAPI)

```powershell
# Navigate to backend
cd rag_system

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and configure your LLM provider:
#   - For Ollama (FREE): Set LLM_PROVIDER=ollama and OLLAMA_BASE_URL
#   - For OpenAI (Paid): Set LLM_PROVIDER=openai and OPENAI_API_KEY

# Start the server
uvicorn app.main:app --reload
# Server runs at http://localhost:8001
# Port is configurable in .env file (default: 8001)
```

### 2️⃣ Web Frontend Setup (Next.js)

```bash
# Navigate to web app
cd rag-web

# Install dependencies
npm install

# Start development server
npm run dev
# App runs at http://localhost:3000
```

### 3️⃣ Mobile App Setup (React Native)

```bash
# Navigate to mobile app
cd rag-mobile

# Install dependencies
npm install

# Start Expo development server
npm start
# Scan QR code with Expo Go app
```

## ✨ Features

### Backend (rag_system)
- ✅ **Authentication & Authorization** - JWT-based user management
- ✅ **Document Processing** - PDF and text file support (up to 100 pages)
- ✅ **Vector Search** - ChromaDB for fast similarity search
- ✅ **AI-Powered Q&A** - OpenAI GPT or Ollama (Local/Remote models)
- ✅ **Flexible LLM Provider** - Switch between OpenAI (paid) and Ollama (free)
- ✅ **Source Citations** - Answers include document references
- ✅ **REST API** - FastAPI with Swagger documentation
- ✅ **Document Management** - Upload, list, and delete documents

### Web Frontend (rag-web)
- ✅ **Modern UI** - Next.js 14 with TypeScript
- ✅ **Authentication Pages** - Login and registration
- ✅ **Document Upload** - Drag-and-drop interface
- ✅ **Chat Interface** - Real-time Q&A with document sources
- ✅ **Document List** - Manage uploaded documents
- ✅ **Responsive Design** - Works on desktop and mobile

### Mobile App (rag-mobile)
- ✅ **Cross-Platform** - iOS and Android support via Expo
- ✅ **Native Authentication** - Secure token storage
- ✅ **Document Upload** - Pick from device storage
- ✅ **Mobile Chat** - Optimized Q&A interface
- ✅ **Offline Support** - Cached document list

## 📚 API Documentation

Once the backend is running, access interactive API docs:

- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

**Note:** If you changed the PORT in `.env`, use your configured port instead of 8001.

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Create new user account |
| POST | `/auth/login` | Login and get JWT token |
| POST | `/upload` | Upload PDF or text document |
| POST | `/query` | Ask questions about documents |
| GET | `/documents` | List all uploaded documents |
| DELETE | `/documents/{id}` | Delete a document |
| GET | `/health` | System health check |

## 🛠️ Technology Stack

### Backend
- **FastAPI** - High-performance Python web framework
- **ChromaDB** - Vector database for embeddings
- **LangChain** - RAG orchestration
- **OpenAI** - GPT-3.5-turbo & embeddings (optional)
- **Ollama** - Local/Remote open-source LLM support (llama3.1, qwen3, gemma3)
- **PyPDF2** - PDF text extraction
- **Python-JOSE** - JWT authentication

### Web Frontend
- **Next.js 14** - React framework with App Router
- **TypeScript** - Type-safe development
- **TailwindCSS** - Utility-first styling
- **Fetch API** - Backend communication

### Mobile App
- **React Native** - Cross-platform mobile framework
- **Expo** - Development and build tooling
- **TypeScript** - Type-safe mobile development

## 🔐 Environment Configuration

### Backend (.env)

#### Option 1: Ollama (FREE - Recommended)

**Local Ollama Server:**
```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:latest

HOST=0.0.0.0
PORT=8001  # Change if port is already in use
SECRET_KEY=your-secret-key-for-jwt
CHROMA_DB_PATH=./data/chroma_db
UPLOAD_DIR=./data/documents
```

**Remote Ollama Server:**
```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://192.168.18.147:11434  # Your Ollama server IP
OLLAMA_MODEL=llama3.1:latest

HOST=0.0.0.0
PORT=8001  # Change if port is already in use
SECRET_KEY=your-secret-key-for-jwt
CHROMA_DB_PATH=./data/chroma_db
UPLOAD_DIR=./data/documents
```

**Setup Ollama:**
```powershell
# 1. Download and install Ollama from https://ollama.ai

# 2. Pull a model (choose one):
ollama pull llama3.1:latest  # 4.9 GB - Best quality
ollama pull llama3:8b         # 4.7 GB - Fast and capable
ollama pull qwen3:8b          # 5.2 GB - Alternative
ollama pull gemma3:1b         # 815 MB - Lightweight

# 3. List installed models:
ollama list

# 4. Start Ollama server (usually auto-starts):
ollama serve
```

#### Option 2: OpenAI (Paid - Cloud API)
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

HOST=0.0.0.0
PORT=8001  # Change if port is already in use
SECRET_KEY=your-secret-key-for-jwt
CHROMA_DB_PATH=./data/chroma_db
UPLOAD_DIR=./data/documents
```

### Web Frontend (.env.local)
```env
NEXT_PUBLIC_API_URL=http://localhost:8001  # Match backend PORT
```

### Mobile App
Edit `services/api.ts` to configure the backend URL:
```typescript
const API_URL = 'http://your-backend-ip:8001';  # Match backend PORT
```

## 📖 Detailed Documentation

For component-specific documentation, see:

- **Backend**: [rag_system/README.md](rag_system/README.md)
- **Web**: [rag-web/README.md](rag-web/README.md)
- **Mobile**: [rag-mobile/README.md](rag-mobile/README.md)

## 🚀 Deployment

### Backend Deployment
- **Railway**: Railway.app (Python support)
- **Render**: render.com (Free tier available)
- **AWS**: EC2 or ECS
- **Docker**: Containerize with provided Dockerfile

### Web Deployment
- **Vercel**: Automatic deployment from GitHub
- **Netlify**: Static site hosting
- **AWS Amplify**: Full-stack hosting

### Mobile Deployment
- **Expo EAS**: Build and submit to app stores
- **App Store**: iOS deployment
- **Google Play**: Android deployment

## 🐛 Troubleshooting

### Backend Issues

**"OpenAI API key not configured" or "Ollama connection error"**
- Ensure `.env` file exists in `rag_system/` 
- For Ollama: Check `OLLAMA_BASE_URL` is correct and Ollama is running
  ```powershell
  # Test Ollama connection
  curl http://localhost:11434/api/tags
  
  # Or for remote server
  curl http://192.168.18.147:11434/api/tags
  ```
- For OpenAI: Verify your API key is valid

**"Model not found" (Ollama)**
- List available models: `ollama list`
- Pull the model: `ollama pull llama3.1:latest`
- Update `OLLAMA_MODEL` in `.env` to match an installed model

**"Cannot connect to remote Ollama server"**
- Ensure remote machine's firewall allows port 11434
- Verify Ollama is bound to 0.0.0.0:
  ```powershell
  # On remote machine, set environment variable:
  $env:OLLAMA_HOST = "0.0.0.0"
  ollama serve
  ```
- Check both machines are on the same network

**"Module not found" errors**
- Activate virtual environment: `.\venv\Scripts\activate`
- Reinstall: `pip install -r requirements.txt`

### Web Issues

**"Cannot connect to API"**
- Ensure backend is running at `http://localhost:8001` (or your configured PORT)
- Check `NEXT_PUBLIC_API_URL` in `.env.local` matches backend PORT
- Verify PORT setting in backend `.env` file

### Mobile Issues

**"Network request failed"**
- Update API URL in `services/api.ts` to your computer's IP
- Ensure phone and computer are on same network

## 📊 Performance

- **Document Processing**: 2-5 seconds for 50-page PDF
- **Query Response**: 1-3 seconds
- **Concurrent Users**: Supports multiple simultaneous users
- **Document Limit**: Up to 100 pages per document

## 🔒 Security

- ✅ JWT-based authentication
- ✅ Password hashing with bcrypt
- ✅ Token expiration (24 hours)
- ✅ CORS configuration
- ⚠️ Remember to change `SECRET_KEY` in production
- ⚠️ Never commit `.env` files

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📝 License

This project is open source and available under the MIT License.

## 👨‍💻 Author

**Samad @ FastNexa**

## 🎯 Roadmap

- [ ] Support for DOCX, HTML, and Markdown files
- [ ] Conversation history and context
- [ ] Multi-language support
- [ ] Document sharing between users
- [ ] Advanced search filters
- [ ] Real-time collaboration
- [ ] Analytics dashboard
- [ ] Mobile offline mode
- [ ] Voice-to-text queries
- [ ] Dark mode support

## 📞 Support

For issues or questions:
1. Check component-specific README files
2. Review API documentation at `/docs`
3. Open an issue on GitHub

---

**Built with ❤️ using FastAPI, Next.js, React Native, ChromaDB, and OpenAI**

#(.venv) PS F:\samad\chatobot\rag-web> npm run dev    
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001