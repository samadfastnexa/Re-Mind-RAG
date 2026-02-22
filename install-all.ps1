# RAG System - Quick Install Script
# Run this to install all dependencies at once

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  RAG System - Installing Dependencies" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# Install Backend Dependencies
Write-Host "[1/3] Installing Backend (Python) Dependencies..." -ForegroundColor Yellow
Set-Location "f:\samad\chatobot\rag_system"
pip install -r requirements.txt
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Backend dependencies installed!" -ForegroundColor Green
} else {
    Write-Host "✗ Error installing backend dependencies" -ForegroundColor Red
}
Write-Host ""

# Install Web App Dependencies
Write-Host "[2/3] Installing Web App (Next.js) Dependencies..." -ForegroundColor Yellow
Set-Location "f:\samad\chatobot\rag-web"
npm install
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Web app dependencies installed!" -ForegroundColor Green
} else {
    Write-Host "✗ Error installing web dependencies" -ForegroundColor Red
}
Write-Host ""

# Install Mobile App Dependencies
Write-Host "[3/3] Installing Mobile App (Expo) Dependencies..." -ForegroundColor Yellow
Set-Location "f:\samad\chatobot\rag-mobile"
npm install
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Mobile app dependencies installed!" -ForegroundColor Green
} else {
    Write-Host "✗ Error installing mobile dependencies" -ForegroundColor Red
}
Write-Host ""

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Add your OpenAI API key to: rag_system\.env" -ForegroundColor White
Write-Host "2. Run: .\start-all.ps1" -ForegroundColor White
Write-Host ""

Set-Location "f:\samad\chatobot"
