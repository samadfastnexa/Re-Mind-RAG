# User Management & Authentication Guide

## Overview

The RAG system now includes **role-based access control (RBAC)** with three user roles:

### User Roles

| Role | Can Upload Docs | Can Query | Can Delete Docs | Can Manage Users |
|------|----------------|-----------|-----------------|------------------|
| **USER** | ❌ No | ✅ Yes | ❌ No | ❌ No |
| **UPLOADER** | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No |
| **ADMIN** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |

### Default Admin Account

When you start the server for the first time, a default admin account is created:

```
Username: admin
Password: admin123
```

**⚠️ IMPORTANT:** Change this password in production!

---

## Installation

Install the new authentication dependencies:

```powershell
cd f:\samad\chatobot\rag_system
.\venv\Scripts\activate
pip install pyjwt==2.8.0 passlib[bcrypt]==1.7.4
```

Or install all dependencies:

```powershell
pip install -r requirements.txt
```

---

## API Endpoints

### 1. Login (Get Access Token)

**POST** `/auth/login`

Get a JWT token to authenticate your requests.

**Request:**
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "admin_001",
    "username": "admin",
    "email": "admin@example.com",
    "role": "admin",
    "is_active": true,
    "created_at": "2026-02-22T10:00:00"
  }
}
```

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

**PowerShell Example:**
```powershell
$response = Invoke-RestMethod -Uri "http://localhost:8000/auth/login" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"username":"admin","password":"admin123"}'

$token = $response.access_token
Write-Host "Token: $token"
```

---

### 2. Get Current User Info

**GET** `/auth/me`

Get information about the currently authenticated user.

**Headers:**
```
Authorization: Bearer <your_token>
```

**cURL Example:**
```bash
curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**PowerShell Example:**
```powershell
$headers = @{
    "Authorization" = "Bearer $token"
}

Invoke-RestMethod -Uri "http://localhost:8000/auth/me" `
  -Method GET `
  -Headers $headers
```

---

### 3. Create User (Admin Only)

**POST** `/auth/register`

Create a new user (only admins can do this).

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Request:**
```json
{
  "username": "john_uploader",
  "email": "john@example.com",
  "password": "secure_password_123",
  "role": "uploader"
}
```

**Response:**
```json
{
  "id": "user_002",
  "username": "john_uploader",
  "email": "john@example.com",
  "role": "uploader",
  "is_active": true,
  "created_at": "2026-02-22T10:30:00"
}
```

**PowerShell Example:**
```powershell
$headers = @{
    "Authorization" = "Bearer $token"
}

$body = @{
    username = "john_uploader"
    email = "john@example.com"
    password = "secure_password_123"
    role = "uploader"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/auth/register" `
  -Method POST `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $body
```

---

### 4. List All Users (Admin Only)

**GET** `/auth/users`

Get a list of all registered users.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**PowerShell Example:**
```powershell
$headers = @{
    "Authorization" = "Bearer $token"
}

Invoke-RestMethod -Uri "http://localhost:8000/auth/users" `
  -Method GET `
  -Headers $headers
```

---

### 5. Upload Document (Uploader/Admin Only)

**POST** `/upload`

Upload a document. **Only users with UPLOADER or ADMIN role can do this.**

**Headers:**
```
Authorization: Bearer <uploader_or_admin_token>
```

**PowerShell Example:**
```powershell
$headers = @{
    "Authorization" = "Bearer $token"
}

$filePath = "C:\path\to\document.pdf"
$fileBytes = [System.IO.File]::ReadAllBytes($filePath)
$boundary = [System.Guid]::NewGuid().ToString()

# Note: Upload requires multipart/form-data
# Use curl or Python for easier multipart upload
```

**cURL Example (easier for file upload):**
```bash
curl -X POST "http://localhost:8000/upload" \
  -H "Authorization: Bearer $token" \
  -F "file=@document.pdf"
```

---

### 6. Query Documents (All Authenticated Users)

**POST** `/query`

Ask questions about documents. **All authenticated users can query.**

**Headers:**
```
Authorization: Bearer <any_user_token>
```

**Request:**
```json
{
  "question": "What is the main topic of the documents?",
  "top_k": 6
}
```

**PowerShell Example:**
```powershell
$headers = @{
    "Authorization" = "Bearer $token"
}

$body = @{
    question = "What is the main topic?"
    top_k = 6
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/query" `
  -Method POST `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $body
```

---

### 7. List Documents (All Authenticated Users)

**GET** `/documents`

List all uploaded documents. **All authenticated users can list.**

**Headers:**
```
Authorization: Bearer <any_user_token>
```

---

### 8. Delete Document (Uploader/Admin Only)

**DELETE** `/documents/{document_id}`

Delete a document. **Only UPLOADER or ADMIN can delete.**

**Headers:**
```
Authorization: Bearer <uploader_or_admin_token>
```

---

## Complete Workflow Examples

### Example 1: Admin Creates an Uploader User

```powershell
# 1. Admin logs in
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8000/auth/login" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"username":"admin","password":"admin123"}'

$adminToken = $loginResponse.access_token

# 2. Admin creates an uploader user
$headers = @{ "Authorization" = "Bearer $adminToken" }

$newUser = @{
    username = "document_uploader"
    email = "uploader@company.com"
    password = "Upload123!"
    role = "uploader"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/auth/register" `
  -Method POST `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $newUser

Write-Host "✅ Uploader user created successfully!"
```

---

### Example 2: Uploader Uploads a Document

```powershell
# 1. Uploader logs in
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8000/auth/login" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"username":"document_uploader","password":"Upload123!"}'

$uploaderToken = $loginResponse.access_token

# 2. Upload document using curl (easier for file upload)
# Save token for later use
Set-Content -Path "uploader_token.txt" -Value $uploaderToken

# Then in bash/curl:
# curl -X POST "http://localhost:8000/upload" \
#   -H "Authorization: Bearer $(cat uploader_token.txt)" \
#   -F "file=@document.pdf"
```

---

### Example 3: Normal User Queries (Cannot Upload)

```powershell
# 1. Admin creates a normal user
$adminToken = "..." # from Example 1

$headers = @{ "Authorization" = "Bearer $adminToken" }

$normalUser = @{
    username = "reader_user"
    email = "reader@company.com"
    password = "Reader123!"
    role = "user"  # Normal user - can only query
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/auth/register" `
  -Method POST `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $normalUser

# 2. Normal user logs in
$userLoginResponse = Invoke-RestMethod -Uri "http://localhost:8000/auth/login" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"username":"reader_user","password":"Reader123!"}'

$userToken = $userLoginResponse.access_token

# 3. Normal user can query ✅
$headers = @{ "Authorization" = "Bearer $userToken" }

$query = @{
    question = "What are the key points?"
    top_k = 6
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/query" `
  -Method POST `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $query

# 4. Normal user CANNOT upload ❌
# This will return 403 Forbidden:
# Invoke-RestMethod -Uri "http://localhost:8000/upload" ...
```

---

## Testing with Swagger UI

1. Open http://localhost:8000/docs
2. Click **"Authorize"** button (🔒 icon at top right)
3. Login first using `/auth/login` endpoint
4. Copy the `access_token` from response
5. Click **"Authorize"** button again
6. Enter: `Bearer <your_token>` (e.g., `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`)
7. Click **"Authorize"** then **"Close"**
8. Now you can test all endpoints with authentication

---

## User Data Storage

Users are stored in: `f:\samad\chatobot\rag_system\data\users.json`

**⚠️ Security Notes:**
- Passwords are hashed using bcrypt
- Never share or commit `users.json` file
- Tokens expire after 24 hours
- In production, use a proper database (PostgreSQL, MySQL)

---

## Security Configuration

### Change JWT Secret Key

⚠️ **IMPORTANT:** Change the secret key in production!

Edit `f:\samad\chatobot\rag_system\app\auth_service.py`:

```python
SECRET_KEY = "your-secret-key-change-in-production"  # Change this!
```

Or better, add to `.env` file:

```env
JWT_SECRET_KEY=your-super-secret-key-minimum-32-characters-long
```

---

## Error Messages

### 401 Unauthorized
```json
{
  "detail": "Incorrect username or password"
}
```
**Solution:** Check credentials

### 403 Forbidden
```json
{
  "detail": "You don't have permission to upload documents. Contact admin for access."
}
```
**Solution:** Contact admin to upgrade your role to UPLOADER

### 403 Forbidden
```json
{
  "detail": "Only admins can create users"
}
```
**Solution:** Only admins can create users

---

## Role Assignment Strategy

### Recommended Setup

For a typical organization:

1. **1-2 Admins** - IT staff, system administrators
2. **5-10 Uploaders** - Content managers, documentation team
3. **Everyone else as Users** - Read-only access to query documents

### Example User Assignments

```
admin@company.com        → ADMIN      (manages system)
content.manager@...       → UPLOADER  (uploads docs)
doc.specialist@...        → UPLOADER  (uploads docs)
sales.team@...            → USER      (queries only)
support.agent@...         → USER      (queries only)
customer.service@...      → USER      (queries only)
```

---

## Migration from No-Auth System

If you have existing web/mobile apps, update them to:

1. Add login screen
2. Store JWT token after login
3. Include token in all API requests:
   ```javascript
   headers: {
     'Authorization': `Bearer ${token}`
   }
   ```

---

## Next Steps

1. ✅ Install dependencies: `pip install -r requirements.txt`
2. ✅ Start server: `uvicorn app.main:app --reload`
3. ✅ Test login with default admin (username: `admin`, password: `admin123`)
4. ✅ Create uploader users for your team
5. ✅ Create normal users for read-only access
6. ✅ Update web/mobile apps to use authentication

---

## Support

If you encounter issues:
- Check token is included in Authorization header
- Verify token format: `Bearer <token>` (with space)
- Check user role matches required permission
- Check token hasn't expired (24 hour lifetime)
