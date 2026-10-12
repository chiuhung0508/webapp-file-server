import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import bcrypt
import jwt
from fastapi import Request, HTTPException, status, Depends
from app.config import (
    SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES,
    STORAGE_DIR, COOKIE_NAME
)
from app.database import get_user_by_username, has_users

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    """Create a signed JWT session token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.now(datetime.timezone.utc) + expires_delta
    else:
        expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT session token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        return None

def get_safe_path(requested_path: str = "", allow_root: bool = False) -> Path:
    """
    Sanitize and resolve a user-supplied path strictly inside the sandboxed STORAGE_DIR.
    Guards against path traversal, symlink breakout, null-bytes, and system escapes.
    """
    if "\x00" in requested_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid path: null bytes detected."
        )

    # Clean leading slashes and relative parent components
    cleaned = requested_path.strip().lstrip("/").lstrip("\\")
    
    # Resolve target path relative to storage root
    target = (STORAGE_DIR / cleaned).resolve()
    storage_root = STORAGE_DIR.resolve()

    # Crucial security check: must be strictly inside or equal to storage root
    try:
        is_inside = target.is_relative_to(storage_root)
    except AttributeError:
        # Fallback for Python < 3.9 (though we are on 3.12)
        try:
            target.relative_to(storage_root)
            is_inside = True
        except ValueError:
            is_inside = False

    if not is_inside:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Path escapes sandboxed storage root."
        )

    if target == storage_root and not allow_root:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Targeting root storage directory for this operation is not permitted."
        )

    return target

async def get_current_user(request: Request) -> Dict[str, Any]:
    """FastAPI dependency to extract and verify the current authenticated user."""
    # First check if the system has been configured
    if not has_users():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server setup incomplete. Administrator account required."
        )

    token = request.cookies.get(COOKIE_NAME)
    if not token:
        # Also check Authorization header as fallback
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in."
        )

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid. Please log in again."
        )

    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims."
        )

    user = get_user_by_username(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists."
        )

    return user
