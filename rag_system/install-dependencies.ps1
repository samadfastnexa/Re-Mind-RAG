# Installation script for dependencies
# Run this if regular pip install fails

Write-Host "Installing RAG System Dependencies..." -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green

# Core packages first
Write-Host "`n[1/6] Installing FastAPI & Server..." -ForegroundColor Cyan
pip install fastapi "uvicorn[standard]" python-multipart slowapi

# LangChain ecosystem
Write-Host "`n[2/6] Installing LangChain..." -ForegroundColor Cyan
pip install langchain langchain-community langchain-ollama

# Vector DB and Search
Write-Host "`n[3/6] Installing ChromaDB and Search..." -ForegroundColor Cyan
pip install chromadb rank-bm25

# ML/AI Models
Write-Host "`n[4/6] Installing ML Models..." -ForegroundColor Cyan
pip install sentence-transformers tiktoken

# Document Processing
Write-Host "`n[5/6] Installing Document Tools..." -ForegroundColor Cyan
pip install pypdf2 python-dotenv pydantic-settings email-validator

# Auth & Security
Write-Host "`n[6/6] Installing Auth & Security..." -ForegroundColor Cyan
pip install "python-jose[cryptography]" "passlib[bcrypt]"

# Additional utilities
Write-Host "`nInstalling Additional Utilities..." -ForegroundColor Cyan
pip install requests numpy aiofiles

# Optional - may fail on some systems
Write-Host "`nInstalling Optional Packages..." -ForegroundColor Yellow
Write-Host "(These may fail - ignore errors)" -ForegroundColor Yellow
pip install langchain-openai langchain-experimental 2>$null

Write-Host "`n==========================================" -ForegroundColor Green
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "`nTo verify, run:" -ForegroundColor Cyan
Write-Host "python -c 'import fastapi, langchain, chromadb; print(""All OK"")'`n" -ForegroundColor White
