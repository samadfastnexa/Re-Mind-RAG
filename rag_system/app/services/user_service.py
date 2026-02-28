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
            can_delete_history INTEGER DEFAULT 1,
            can_export INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)
    
    # Migration: Add can_delete_history column if it doesn't exist
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'can_delete_history' not in columns:
        print("Migrating database: Adding can_delete_history column...")
        cursor.execute("ALTER TABLE users ADD COLUMN can_delete_history INTEGER DEFAULT 1")
        print("✓ Database migration complete")
    
    # Migration: Add can_export column if it doesn't exist
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'can_export' not in columns:
        print("Migrating database: Adding can_export column...")
        cursor.execute("ALTER TABLE users ADD COLUMN can_export INTEGER DEFAULT 1")
        print("✓ Database migration complete")
    
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
            can_delete_history=bool(row["can_delete_history"] if "can_delete_history" in row.keys() else 1),
            can_export=bool(row["can_export"] if "can_export" in row.keys() else 1),
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
            can_delete_history=bool(row["can_delete_history"] if "can_delete_history" in row.keys() else 1),
            can_export=bool(row["can_export"] if "can_export" in row.keys() else 1),
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
        INSERT INTO users (username, email, hashed_password, role, can_delete_history, can_export, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user.username,
        user.email,
        hashed_password,
        user.role.value,
        1,  # Default: can delete history
        1,  # Default: can export
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
        can_delete_history=True,
        can_export=True,
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
            can_delete_history=bool(row["can_delete_history"] if "can_delete_history" in row.keys() else 1),
            can_export=bool(row["can_export"] if "can_export" in row.keys() else 1),
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


def update_user(user_id: int, username: str = None, email: str = None, password: str = None, role: UserRole = None, is_active: bool = None) -> Optional[UserInDB]:
    """Update user information by ID."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Verify user exists
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        return None

    updates = []
    params = []

    if username is not None:
        # Check uniqueness
        cursor.execute("SELECT id FROM users WHERE username = ? AND id != ?", (username, user_id))
        if cursor.fetchone():
            conn.close()
            raise ValueError("Username already taken")
        updates.append("username = ?")
        params.append(username)

    if email is not None:
        cursor.execute("SELECT id FROM users WHERE email = ? AND id != ?", (email, user_id))
        if cursor.fetchone():
            conn.close()
            raise ValueError("Email already taken")
        updates.append("email = ?")
        params.append(email)

    if password is not None:
        updates.append("hashed_password = ?")
        params.append(get_password_hash(password))

    if role is not None:
        updates.append("role = ?")
        params.append(role.value)

    if is_active is not None:
        updates.append("is_active = ?")
        params.append(1 if is_active else 0)

    if not updates:
        conn.close()
        return None

    params.append(user_id)
    query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
    cursor.execute(query, params)
    conn.commit()

    # Fetch updated user
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
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
            can_delete_history=bool(row["can_delete_history"] if "can_delete_history" in row.keys() else 1),
            created_at=datetime.fromisoformat(row["created_at"])
        )
    return None


def delete_user(user_id: int) -> bool:
    """Delete a user by ID."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()

    return success


def update_user_permission(user_id: int, can_delete_history: bool = None, can_export: bool = None) -> bool:
    """Update user's permissions (admin only)."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if can_delete_history is not None:
        updates.append("can_delete_history = ?")
        params.append(1 if can_delete_history else 0)
    
    if can_export is not None:
        updates.append("can_export = ?")
        params.append(1 if can_export else 0)
    
    if not updates:
        conn.close()
        return False
    
    params.append(user_id)
    query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
    
    cursor.execute(query, tuple(params))
    
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    return success
