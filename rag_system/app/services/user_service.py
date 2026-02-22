"""
User Service - Manages user database operations
Uses SQLite for simple user management
"""
import sqlite3
from datetime import datetime
from typing import Optional
from pathlib import Path
from app.auth_models import UserInDB, UserCreate, UserRole
from app.auth_utils import get_password_hash


# Database file path
DB_PATH = Path("./data/users.db")


def init_user_database():
    """Initialize the user database with tables."""
    # Ensure data directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            role TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)
    
    conn.commit()
    
    # Check if admin user exists, if not create default admin
    cursor.execute("SELECT * FROM users WHERE role = 'admin'")
    admin_exists = cursor.fetchone()
    
    if not admin_exists:
        # Create default admin user
        print("Creating default admin user...")
        cursor.execute("""
            INSERT INTO users (username, email, hashed_password, role, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "admin",
            "admin@example.com",
            get_password_hash("admin123"),  # Default password: admin123
            UserRole.ADMIN.value,
            datetime.utcnow().isoformat()
        ))
        conn.commit()
        print("✓ Default admin user created (username: admin, password: admin123)")
        print("⚠️  IMPORTANT: Change the admin password immediately!")
    
    conn.close()


def get_user_by_username(username: str) -> Optional[UserInDB]:
    """Get user by username."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return UserInDB(
            id=row["id"],
            username=row["username"],
            email=row["email"],
            hashed_password=row["hashed_password"],
            role=UserRole(row["role"]),
            is_active=bool(row["is_active"]),
            created_at=datetime.fromisoformat(row["created_at"])
        )
    return None


def get_user_by_email(email: str) -> Optional[UserInDB]:
    """Get user by email."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return UserInDB(
            id=row["id"],
            username=row["username"],
            email=row["email"],
            hashed_password=row["hashed_password"],
            role=UserRole(row["role"]),
            is_active=bool(row["is_active"]),
            created_at=datetime.fromisoformat(row["created_at"])
        )
    return None


def create_user(user: UserCreate) -> UserInDB:
    """Create a new user."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    hashed_password = get_password_hash(user.password)
    created_at = datetime.utcnow().isoformat()
    
    cursor.execute("""
        INSERT INTO users (username, email, hashed_password, role, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        user.username,
        user.email,
        hashed_password,
        user.role.value,
        created_at
    ))
    
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return UserInDB(
        id=user_id,
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        role=user.role,
        is_active=True,
        created_at=datetime.fromisoformat(created_at)
    )


def get_all_users() -> list[UserInDB]:
    """Get all users."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    
    users = []
    for row in rows:
        users.append(UserInDB(
            id=row["id"],
            username=row["username"],
            email=row["email"],
            hashed_password=row["hashed_password"],
            role=UserRole(row["role"]),
            is_active=bool(row["is_active"]),
            created_at=datetime.fromisoformat(row["created_at"])
        ))
    
    return users


def update_user_role(username: str, new_role: UserRole) -> bool:
    """Update user role (admin only)."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE users SET role = ? WHERE username = ?",
        (new_role.value, username)
    )
    
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    return success


def deactivate_user(username: str) -> bool:
    """Deactivate a user."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE users SET is_active = 0 WHERE username = ?",
        (username,)
    )
    
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    return success


def activate_user(username: str) -> bool:
    """Activate a user."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE users SET is_active = 1 WHERE username = ?",
        (username,)
    )
    
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    return success
