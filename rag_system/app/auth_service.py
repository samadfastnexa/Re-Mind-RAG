"""
Authentication and authorization service.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict
import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.user_models import User, UserCreate, UserRole, TokenData
import json
from pathlib import Path

# Security configuration
SECRET_KEY = "your-secret-key-change-in-production"  # TODO: Move to .env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Password hashing — rounds=10 matches auth_utils.py for consistent performance
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=10)

# HTTP Bearer token scheme
security = HTTPBearer()

# Simple file-based user storage (replace with real DB in production)
USERS_FILE = Path("./data/users.json")


class AuthService:
    """Handle authentication and authorization."""
    
    def __init__(self):
        self.users_db: Dict[str, dict] = self._load_users()
        
        # Create default admin if no users exist
        if not self.users_db:
            self._create_default_admin()
    
    def _load_users(self) -> Dict[str, dict]:
        """Load users from file."""
        if USERS_FILE.exists():
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_users(self):
        """Save users to file."""
        USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(USERS_FILE, 'w') as f:
            json.dump(self.users_db, f, indent=2, default=str)
    
    def _create_default_admin(self):
        """Create default admin user."""
        admin_user = {
            "id": "admin_001",
            "username": "admin",
            "email": "admin@example.com",
            "password_hash": self.hash_password("admin123"),
            "role": UserRole.ADMIN.value,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat()
        }
        self.users_db["admin"] = admin_user
        self._save_users()
        print("✅ Default admin created: username='admin', password='admin123'")
    
    def hash_password(self, password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    def create_user(self, user_create: UserCreate, creator_role: UserRole) -> User:
        """
        Create a new user.
        
        Only admins can create users.
        """
        if creator_role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can create users"
            )
        
        # Check if username exists
        if user_create.username in self.users_db:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        
        # Create user
        user_id = f"user_{len(self.users_db) + 1:03d}"
        user_data = {
            "id": user_id,
            "username": user_create.username,
            "email": user_create.email,
            "password_hash": self.hash_password(user_create.password),
            "role": user_create.role.value,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat()
        }
        
        self.users_db[user_create.username] = user_data
        self._save_users()
        
        # Return user without password
        return User(**{k: v for k, v in user_data.items() if k != "password_hash"})
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user."""
        user_data = self.users_db.get(username)
        if not user_data:
            return None
        
        if not self.verify_password(password, user_data["password_hash"]):
            return None
        
        if not user_data.get("is_active"):
            return None
        
        # Update last login
        user_data["last_login"] = datetime.utcnow().isoformat()
        self._save_users()
        
        return User(**{k: v for k, v in user_data.items() if k != "password_hash"})
    
    def create_access_token(self, user: User) -> str:
        """Create JWT access token."""
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode = {
            "user_id": user.id,
            "username": user.username,
            "role": user.role.value,
            "exp": expire
        }
        
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def decode_token(self, token: str) -> TokenData:
        """Decode and validate JWT token."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("user_id")
            username = payload.get("username")
            role = payload.get("role")
            
            if user_id is None or username is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )
            
            return TokenData(
                user_id=user_id,
                username=username,
                role=UserRole(role)
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    def get_user(self, username: str) -> Optional[User]:
        """Get user by username."""
        user_data = self.users_db.get(username)
        if user_data:
            return User(**{k: v for k, v in user_data.items() if k != "password_hash"})
        return None
    
    def list_users(self, requester_role: UserRole) -> list:
        """List all users (admin only)."""
        if requester_role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can list users"
            )
        
        return [
            User(**{k: v for k, v in user.items() if k != "password_hash"})
            for user in self.users_db.values()
        ]


# Global auth service instance
auth_service = AuthService()


# Dependency functions for FastAPI
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """
    Get current authenticated user from JWT token.
    
    Usage in endpoint:
    async def my_endpoint(current_user: TokenData = Depends(get_current_user)):
    """
    token = credentials.credentials
    return auth_service.decode_token(token)


async def require_uploader(
    current_user: TokenData = Depends(get_current_user)
) -> TokenData:
    """
    Require user to have UPLOADER or ADMIN role.
    
    Use this for document upload endpoints.
    """
    if current_user.role not in [UserRole.UPLOADER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to upload documents. Contact admin for access."
        )
    return current_user


async def require_admin(
    current_user: TokenData = Depends(get_current_user)
) -> TokenData:
    """
    Require user to have ADMIN role.
    
    Use this for admin-only endpoints.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user
