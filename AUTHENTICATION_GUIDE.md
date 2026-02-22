# User Management & Authentication Setup

## Overview

Your RAG system now has **role-based authentication** with two user roles:
- **👤 USER**: Can query documents and view document list (read-only)
- **👑 ADMIN**: Can upload documents, delete documents, query, and manage users

## Default Credentials

**Admin Account:**
- Username: `admin`
- Password: `admin123`

⚠️ **IMPORTANT**: Change the admin password after first login!

## User Roles & Permissions

| Feature | USER Role | ADMIN Role |
|---------|-----------|------------|
| View Documents | ✅ | ✅ |
| Query/Chat | ✅ | ✅ |
| Upload Documents | ❌ | ✅ |
| Delete Documents | ❌ | ✅ |
| Create Users | ❌ | ✅ |

## How It Works

### Backend Authentication
- **JWT Tokens**: Secure token-based authentication
- **Password Hashing**: Bcrypt for password security
- **SQLite Database**: User data stored in `./data/users.db`
- **Token Expiry**: 24 hours (configurable in `.env`)

### Frontend Authentication
- **Login Page**: `/login` route
- **Token Storage**: LocalStorage for persistence
- **Auto-Redirect**: Unauthenticated users redirected to login
- **Conditional UI**: Upload/delete features hidden for non-admin users

## API Endpoints

### Authentication Endpoints

#### 1. Login
```
POST /api/auth/login
Content-Type: application/x-www-form-urlencoded

username=admin&password=admin123
```

Response:
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

#### 2. Get Current User
```
GET /api/auth/me
Authorization: Bearer <token>
```

Response:
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "role": "admin",
  "is_active": true,
  "created_at": "2026-02-23T..."
}
```

#### 3. Register New User (Admin Only)
```
POST /api/auth/register
Authorization: Bearer <admin-token>
Content-Type: application/json

{
  "username": "john",
  "email": "john@example.com",
  "password": "secure123",
  "role": "user"
}
```

#### 4. List All Users (Admin Only)
```
GET /api/auth/users
Authorization: Bearer <admin-token>
```

### Protected Document Endpoints

All document endpoints now require authentication:

```
GET /documents
Authorization: Bearer <token>

POST /upload (ADMIN only)
Authorization: Bearer <admin-token>

DELETE /documents/{id} (ADMIN only)
Authorization: Bearer <admin-token>

POST /query
Authorization: Bearer <token>
```

## Using the Web App

### 1. Login
1. Navigate to `http://localhost:3000`
2. You'll be redirected to `/login`
3. Enter credentials:
   - Username: `admin`
   - Password: `admin123`
4. Click "Sign In"

### 2. Admin Users
- Can see **Upload** section
- Can upload documents
- Can delete documents
- Can query documents
- Can view all documents

### 3. Regular Users
- Can query documents
- Can view all documents
- **Cannot** upload or delete documents
- Upload/delete buttons are hidden

## Creating New Users

### Using API (Recommended)

1. Login as admin to get token
2. Call the register endpoint:

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "email": "alice@example.com",
    "password": "securePass123",
    "role": "user"
  }'
```

### Using Database Directly

```python
# Run this in Python console with venv activated
from app.services.user_service import create_user
from app.auth_models import UserCreate, UserRole

new_user = UserCreate(
    username="bob",
    email="bob@example.com",
    password="password123",
    role=UserRole.ADMIN  # or UserRole.USER
)

created_user = create_user(new_user)
print(f"User created: {created_user.username}")
```

## Security Configuration

### JWT Secret Key (.env)

```env
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

**Generate a secure key for production:**
```bash
openssl rand -hex 32
```

Then update your `.env` file with the generated key.

### Password Requirements

Current requirements:
- Minimum 6 characters
- No complexity requirements (add in production)

To add complexity requirements, update `app/auth_models.py`:
```python
from pydantic import validator

class UserCreate(BaseModel):
    password: str = Field(..., min_length=8)
    
    @validator('password')
    def validate_password(cls, v):
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        return v
```

## Database Schema

**Users Table** (`./data/users.db`):
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    role TEXT NOT NULL,  -- 'user' or 'admin'
    is_active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);
```

## Testing Authentication

### 1. Test Login
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

### 2. Test Protected Endpoint
```bash
# Get token from login response
TOKEN="your-token-here"

curl http://localhost:8000/documents \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Test Admin-Only Endpoint
```bash
curl -X POST http://localhost:8000/upload \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -F "file=@document.pdf"
```

## Troubleshooting

### "Could not validate credentials"
- Token expired (24 hours by default)
- Invalid token
- **Solution**: Login again to get a new token

### "You do not have permission to upload documents"
- User role is not 'admin'
- **Solution**: Ask admin to change your role or create admin account

### "Failed to fetch documents" (401 Error)
- Not authenticated
- Token not sent with request
- **Solution**: Login first, ensure token is stored

### Database Locked
- Multiple processes accessing SQLite
- **Solution**: Restart the backend server

## Next Steps - Production Hardening

### 1. Change Default Admin Password
```python
# Update password in database or create new admin
from app.services.user_service import get_user_by_username, update_user_password
from app.auth_utils import get_password_hash

# You'll need to implement update_user_password function
```

### 2. Use Strong JWT Secret
```bash
# Generate and update .env
openssl rand -hex 32
```

### 3. Enable HTTPS
- Use reverse proxy (NGINX)
- Get SSL certificate (Let's Encrypt)
- Update CORS origins to HTTPS URLs

### 4. Add Password Complexity Rules
- Minimum 12 characters
- Require uppercase, lowercase, numbers, symbols
- Check against common password lists

### 5. Add Rate Limiting
```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/auth/login")
@limiter.limit("5/minute")
async def login(...):
    ...
```

### 6. Add Password Reset Flow
- Email verification
- Temporary reset tokens
- Secure reset links

### 7. Implement Session Management
- Token refresh mechanism
- Token revocation list
- Session timeout warnings

## Files Created

- `app/auth_models.py` - User models and schemas
- `app/auth_utils.py` - JWT and password utilities
- `app/services/user_service.py` - User database operations
- `app/page/login/page.tsx` - Login UI component
- Updated `app/main.py` - Auth endpoints and protection
- Updated `lib/api.ts` - Auth client functions
- Updated `.env` - JWT configuration

## Summary

✅ **What you have now:**
- Secure JWT-based authentication
- Role-based access control (User vs Admin)
- Protected document upload (admin-only)
- All users can query and view documents
- Login page with default credentials shown
- Token-based API communication
- User management database

✅ **What users see:**
- **Regular users**: Can only chat and view documents
- **Admin users**: Can upload, delete, chat, and manage

⚠️ **Before production:**
- Change admin password
- Generate new JWT secret key
- Enable HTTPS
- Add password complexity rules
- Implement rate limiting
- Add audit logging
