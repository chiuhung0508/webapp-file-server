import tempfile
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
import aiofiles
from app.security import get_current_user, get_safe_path
from app.config import STORAGE_DIR

router = APIRouter(prefix="/api/editor", tags=["editor"], dependencies=[Depends(get_current_user)])

MAX_EDIT_SIZE = 10 * 1024 * 1024  # 10 MB

LANGUAGE_MODES = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".md": "markdown",
    ".markdown": "markdown",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "css",
    ".sh": "shell",
    ".bash": "shell",
    ".sql": "sql",
    ".xml": "xml",
    ".svg": "xml",
    ".c": "clike",
    ".cpp": "clike",
    ".h": "clike",
    ".java": "clike",
    ".go": "go",
    ".rs": "rust"
}

def detect_language(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return LANGUAGE_MODES.get(ext, "plain")

class SaveFileRequest(BaseModel):
    path: str
    content: str
    create_if_missing: bool = False

@router.get("/read")
async def read_file(path: str = Query(..., description="Relative file path")):
    """Read a text file's contents for online editing."""
    target = get_safe_path(path, allow_root=False)

    if not target.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File does not exist."
        )

    if target.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot open a directory as a text file."
        )

    size = target.stat().st_size
    if size > MAX_EDIT_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum online editable size ({MAX_EDIT_SIZE // (1024 * 1024)}MB)."
        )

    try:
        async with aiofiles.open(target, mode="r", encoding="utf-8") as f:
            content = await f.read()
    except UnicodeDecodeError:
        # Try latin-1 fallback
        try:
            async with aiofiles.open(target, mode="r", encoding="latin-1") as f:
                content = await f.read()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="File appears to be binary and cannot be edited in the text editor."
            )

    rel_path = str(target.resolve().relative_to(STORAGE_DIR.resolve())).replace("\\", "/")

    return {
        "filename": target.name,
        "path": rel_path,
        "content": content,
        "size": size,
        "language": detect_language(target.name)
    }

@router.post("/save")
async def save_file(data: SaveFileRequest):
    """Atomically save changes to a text file online."""
    target = get_safe_path(data.path, allow_root=False)

    if not target.exists() and not data.create_if_missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target file does not exist."
        )

    if target.exists() and target.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target path is a directory."
        )

    # Ensure parent directory exists
    target.parent.mkdir(parents=True, exist_ok=True)

    # Atomic write to temporary file in same directory then replace
    try:
        temp_file = target.with_suffix(f".tmp_{target.suffix}")
        async with aiofiles.open(temp_file, mode="w", encoding="utf-8") as f:
            await f.write(data.content)
        temp_file.replace(target)

        rel_path = str(target.resolve().relative_to(STORAGE_DIR.resolve())).replace("\\", "/")
        return {
            "message": "File saved successfully.",
            "path": rel_path,
            "size": target.stat().st_size
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
