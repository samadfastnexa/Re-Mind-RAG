# Re-Mind RAG - Intelligent Document Q&A System

A full-stack **Retrieval-Augmented Generation (RAG)** system with authentication, enabling users to upload documents and ask AI-powered questions. Built with FastAPI, Next.js, and React Native.

## 🌟 Overview

Re-Mind RAG is a complete document intelligence platform that allows users to:
- 📄 Upload PDF and text documents
- 🤖 Ask questions and get AI-powered answers with source citations
- 🔐 Secure user authentication and authorization
- 💻 Access via web browser or mobile app
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
- **OpenAI API Key** ([Get here](https://platform.openai.com/api-keys))

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
# Edit .env and add your OPENAI_API_KEY

# Start the server
uvicorn app.main:app --reload
# Server runs at http://localhost:8000
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
- ✅ **AI-Powered Q&A** - OpenAI GPT-3.5-turbo integration
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

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

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
- **OpenAI** - GPT-3.5-turbo & embeddings
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
```env
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-3.5-turbo
EMBEDDING_MODEL=text-embedding-3-small
SECRET_KEY=your-secret-key-for-jwt
CHROMA_DB_PATH=./data/chroma_db
UPLOAD_DIR=./data/documents
```

### Web Frontend (.env.local)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Mobile App
Edit `services/api.ts` to configure the backend URL:
```typescript
const API_URL = 'http://your-backend-ip:8000';
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

**"OpenAI API key not configured"**
- Ensure `.env` file exists in `rag_system/` with valid API key

**"Module not found" errors**
- Activate virtual environment: `.\venv\Scripts\activate`
- Reinstall: `pip install -r requirements.txt`

### Web Issues

**"Cannot connect to API"**
- Ensure backend is running at `http://localhost:8000`
- Check `NEXT_PUBLIC_API_URL` in `.env.local`

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
