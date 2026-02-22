# RAG System - Start All Services
# This script opens 3 terminal windows for Backend, Web, and Mobile

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  RAG System - Starting All Services" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# Check if OpenAI API key is configured
$envFile = "f:\samad\chatobot\rag_system\.env"
$content = Get-Content $envFile -Raw
if ($content -match "OPENAI_API_KEY=your_openai_api_key_here") {
    Write-Host "⚠️  WARNING: OpenAI API key not configured!" -ForegroundColor Red
    Write-Host "   Please edit: rag_system\.env" -ForegroundColor Yellow
    Write-Host "   And add your OpenAI API key" -ForegroundColor Yellow
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne "y") {
        exit
    }
}

Write-Host "Starting services in separate windows..." -ForegroundColor Yellow
Write-Host ""

# Start Backend API
Write-Host "🚀 [1/3] Starting Backend API..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'f:\samad\chatobot'; & .\.venv\Scripts\Activate.ps1; cd rag_system; Write-Host '🔧 Backend API Server' -ForegroundColor Green; Write-Host 'Running at: http://localhost:8000' -ForegroundColor Yellow; Write-Host 'API Docs: http://localhost:8000/docs' -ForegroundColor Yellow; Write-Host 'Login: http://localhost:3000/login' -ForegroundColor Yellow; Write-Host ''; python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

Start-Sleep -Seconds 2

# Start Web App
Write-Host "🌐 [2/3] Starting Web App..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'f:\samad\chatobot\rag-web'; Write-Host '🌐 Web Application' -ForegroundColor Green; Write-Host 'Running at: http://localhost:3000' -ForegroundColor Yellow; Write-Host ''; npm run dev"

Start-Sleep -Seconds 2

# Start Mobile App
Write-Host "📱 [3/3] Starting Mobile App..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'f:\samad\chatobot\rag-mobile'; Write-Host '📱 Mobile Application' -ForegroundColor Green; Write-Host 'Scan QR code with Expo Go app' -ForegroundColor Yellow; Write-Host ''; npx expo start"

Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  All Services Started!" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📝 Quick Access:" -ForegroundColor Yellow
Write-Host "   Backend API:  http://localhost:8000" -ForegroundColor White
Write-Host "   API Docs:     http://localhost:8000/docs" -ForegroundColor White
Write-Host "   Web App:      http://localhost:3000" -ForegroundColor White
Write-Host "   Mobile App:   Scan QR code with Expo Go" -ForegroundColor White
Write-Host ""
Write-Host "Press any key to close this window..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
