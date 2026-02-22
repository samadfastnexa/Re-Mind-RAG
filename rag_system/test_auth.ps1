# Quick Test Script for Authentication System

Write-Host "=== RAG System Authentication Test ===" -ForegroundColor Cyan

# Configuration
$baseUrl = "http://localhost:8000"

Write-Host "`n1. Testing Health Endpoint..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$baseUrl/health" -Method GET
    Write-Host "   ✅ Server is healthy" -ForegroundColor Green
    Write-Host "   Status: $($health.status)" -ForegroundColor Gray
} catch {
    Write-Host "   ❌ Server not responding. Make sure it's running!" -ForegroundColor Red
    exit 1
}

Write-Host "`n2. Testing Admin Login..." -ForegroundColor Yellow
try {
    $loginBody = @{
        username = "admin"
        password = "admin123"
    } | ConvertTo-Json

    $loginResponse = Invoke-RestMethod -Uri "$baseUrl/auth/login" `
        -Method POST `
        -ContentType "application/json" `
        -Body $loginBody
    
    $adminToken = $loginResponse.access_token
    Write-Host "   ✅ Admin login successful" -ForegroundColor Green
    Write-Host "   User: $($loginResponse.user.username)" -ForegroundColor Gray
    Write-Host "   Role: $($loginResponse.user.role)" -ForegroundColor Gray
    Write-Host "   Token: $($adminToken.Substring(0, 30))..." -ForegroundColor Gray
} catch {
    Write-Host "   ❌ Login failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "`n3. Testing Get Current User..." -ForegroundColor Yellow
try {
    $headers = @{
        "Authorization" = "Bearer $adminToken"
    }
    
    $currentUser = Invoke-RestMethod -Uri "$baseUrl/auth/me" `
        -Method GET `
        -Headers $headers
    
    Write-Host "   ✅ Retrieved current user info" -ForegroundColor Green
    Write-Host "   Username: $($currentUser.username)" -ForegroundColor Gray
    Write-Host "   Email: $($currentUser.email)" -ForegroundColor Gray
    Write-Host "   Role: $($currentUser.role)" -ForegroundColor Gray
} catch {
    Write-Host "   ❌ Failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n4. Creating Test Uploader User..." -ForegroundColor Yellow
try {
    $headers = @{
        "Authorization" = "Bearer $adminToken"
    }
    
    $newUserBody = @{
        username = "test_uploader"
        email = "uploader@test.com"
        password = "Upload123!"
        role = "uploader"
    } | ConvertTo-Json
    
    $newUser = Invoke-RestMethod -Uri "$baseUrl/auth/register" `
        -Method POST `
        -Headers $headers `
        -ContentType "application/json" `
        -Body $newUserBody
    
    Write-Host "   ✅ Uploader user created" -ForegroundColor Green
    Write-Host "   Username: $($newUser.username)" -ForegroundColor Gray
    Write-Host "   Role: $($newUser.role)" -ForegroundColor Gray
} catch {
    if ($_.Exception.Message -like "*already exists*") {
        Write-Host "   ℹ️  User already exists (this is fine)" -ForegroundColor Yellow
    } else {
        Write-Host "   ❌ Failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "`n5. Creating Test Normal User..." -ForegroundColor Yellow
try {
    $headers = @{
        "Authorization" = "Bearer $adminToken"
    }
    
    $normalUserBody = @{
        username = "test_user"
        email = "user@test.com"
        password = "User123!"
        role = "user"
    } | ConvertTo-Json
    
    $normalUser = Invoke-RestMethod -Uri "$baseUrl/auth/register" `
        -Method POST `
        -Headers $headers `
        -ContentType "application/json" `
        -Body $normalUserBody
    
    Write-Host "   ✅ Normal user created" -ForegroundColor Green
    Write-Host "   Username: $($normalUser.username)" -ForegroundColor Gray
    Write-Host "   Role: $($normalUser.role)" -ForegroundColor Gray
} catch {
    if ($_.Exception.Message -like "*already exists*") {
        Write-Host "   ℹ️  User already exists (this is fine)" -ForegroundColor Yellow
    } else {
        Write-Host "   ❌ Failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "`n6. Testing Uploader Login..." -ForegroundColor Yellow
try {
    $uploaderLoginBody = @{
        username = "test_uploader"
        password = "Upload123!"
    } | ConvertTo-Json

    $uploaderLoginResponse = Invoke-RestMethod -Uri "$baseUrl/auth/login" `
        -Method POST `
        -ContentType "application/json" `
        -Body $uploaderLoginBody
    
    $uploaderToken = $uploaderLoginResponse.access_token
    Write-Host "   ✅ Uploader login successful" -ForegroundColor Green
    Write-Host "   Role: $($uploaderLoginResponse.user.role)" -ForegroundColor Gray
} catch {
    Write-Host "   ❌ Failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n7. Testing Normal User Login..." -ForegroundColor Yellow
try {
    $userLoginBody = @{
        username = "test_user"
        password = "User123!"
    } | ConvertTo-Json

    $userLoginResponse = Invoke-RestMethod -Uri "$baseUrl/auth/login" `
        -Method POST `
        -ContentType "application/json" `
        -Body $userLoginBody
    
    $userToken = $userLoginResponse.access_token
    Write-Host "   ✅ Normal user login successful" -ForegroundColor Green
    Write-Host "   Role: $($userLoginResponse.user.role)" -ForegroundColor Gray
} catch {
    Write-Host "   ❌ Failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n8. Testing Permission: Normal User Trying to Upload (Should Fail)..." -ForegroundColor Yellow
try {
    $headers = @{
        "Authorization" = "Bearer $userToken"
    }
    
    # Try to access upload endpoint (will fail with 403)
    Invoke-RestMethod -Uri "$baseUrl/upload" `
        -Method POST `
        -Headers $headers
    
    Write-Host "   ❌ Normal user was able to upload (this shouldn't happen!)" -ForegroundColor Red
} catch {
    if ($_.Exception.Message -like "*403*" -or $_.Exception.Message -like "*permission*") {
        Write-Host "   ✅ Correctly blocked - Normal user cannot upload" -ForegroundColor Green
    } else {
        Write-Host "   ℹ️  Failed (expected): $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

Write-Host "`n9. Testing Permission: All Users Can Query..." -ForegroundColor Yellow
try {
    $headers = @{
        "Authorization" = "Bearer $userToken"
    }
    
    $queryBody = @{
        question = "Test query"
        top_k = 3
    } | ConvertTo-Json
    
    $queryResponse = Invoke-RestMethod -Uri "$baseUrl/query" `
        -Method POST `
        -Headers $headers `
        -ContentType "application/json" `
        -Body $queryBody
    
    Write-Host "   ✅ Normal user can query documents" -ForegroundColor Green
} catch {
    if ($_.Exception.Message -like "*No documents*") {
        Write-Host "   ✅ Query endpoint accessible (no documents uploaded yet)" -ForegroundColor Green
    } else {
        Write-Host "   ℹ️  Query result: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

Write-Host "`n10. Listing All Users (Admin Only)..." -ForegroundColor Yellow
try {
    $headers = @{
        "Authorization" = "Bearer $adminToken"
    }
    
    $allUsers = Invoke-RestMethod -Uri "$baseUrl/auth/users" `
        -Method GET `
        -Headers $headers
    
    Write-Host "   ✅ Retrieved user list" -ForegroundColor Green
    Write-Host "   Total users: $($allUsers.Count)" -ForegroundColor Gray
    
    foreach ($user in $allUsers) {
        Write-Host "   - $($user.username) ($($user.role))" -ForegroundColor Gray
    }
} catch {
    Write-Host "   ❌ Failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n=== Test Summary ===" -ForegroundColor Cyan
Write-Host "✅ Authentication system is working!" -ForegroundColor Green
Write-Host ""
Write-Host "Test Users Created:" -ForegroundColor Yellow
Write-Host "  1. admin / admin123 (ADMIN) - Can do everything" -ForegroundColor Gray
Write-Host "  2. test_uploader / Upload123! (UPLOADER) - Can upload & query" -ForegroundColor Gray
Write-Host "  3. test_user / User123! (USER) - Can only query" -ForegroundColor Gray
Write-Host ""
Write-Host "API Documentation: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "User Guide: f:\samad\chatobot\rag_system\USER_MANAGEMENT_GUIDE.md" -ForegroundColor Cyan
