"""
Authentication Models and Schemas
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """User roles with different permissions"""
    ADMIN = "admin"  # Can upload documents and query
    USER = "user"    # Can only query, cannot upload


class UserInDB(BaseModel):
    """User model stored in database"""
    id: int
    username: str
    email: EmailStr
    hashed_password: str
    role: UserRole
    is_active: bool = True
    can_delete_history: bool = True  # Permission to delete conversation history
    can_export: bool = True  # Permission to export conversations
    created_at: datetime


class UserCreate(BaseModel):
    """Schema for creating a new user"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: UserRole = UserRole.USER  # Default to USER role


class UserResponse(BaseModel):
    """Schema for user response (without password)"""
    id: int
    username: str
    email: EmailStr
    role: UserRole
    is_active: bool
    can_delete_history: bool
    can_export: bool
    created_at: datetime


class UserUpdate(BaseModel):
    """Schema for updating user information"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserLogin(BaseModel):
    """Schema for user login"""
    username: str
    password: str


class Token(BaseModel):
    """Schema for JWT token response"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for token payload data"""
    username: Optional[str] = None
    role: Optional[UserRole] = None
