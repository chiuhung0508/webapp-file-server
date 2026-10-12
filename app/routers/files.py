import os
import shutil
import mimetypes
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from app.security import get_current_user, get_safe_path
from app.config import STORAGE_DIR

router = APIRouter(prefix="/api/files", tags=["files"], dependencies=[Depends(get_current_user)])

TEXT_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".json", ".yaml", ".yml", ".py", ".js", ".ts",
    ".jsx", ".tsx", ".html", ".htm", ".css", ".scss", ".sh", ".bash", ".csv",
    ".log", ".xml", ".svg", ".ini", ".conf", ".cfg", ".toml", ".env", ".sql",
    ".dockerfile", ".gitignore", ".c", ".cpp", ".h", ".rs", ".go", ".java", ".php"
}

def is_text_file(filename: str) -> bool:
    ext = Path(filename).suffix.lower()
    if ext in TEXT_EXTENSIONS or filename.lower().startswith(".env"):
        return True
    mime, _ = mimetypes.guess_type(filename)
    if mime and (mime.startswith("text/") or mime in ("application/json", "application/javascript", "application/xml")):
        return True
    return False

class MkdirRequest(BaseModel):
    parent_path: str = ""
    folder_name: str = Field(..., min_length=1, max_length=255)

class RenameRequest(BaseModel):
    path: str
    new_name: str = Field(..., min_length=1, max_length=255)

class DeleteRequest(BaseModel):
    path: str

@router.get("/list")
async def list_files(path: str = Query("", description="Relative path within storage")):
    """List contents of a directory with rich metadata."""
    dir_path = get_safe_path(path, allow_root=True)

    if not dir_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Directory not found."
        )

    if not dir_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Specified path is a file, not a directory."
        )

    items: List[Dict[str, Any]] = []
    
    try:
        entries = list(dir_path.iterdir())
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied accessing directory."
        )

    # Sort folders first, then alphabetical
    entries.sort(key=lambda x: (not x.is_dir(), x.name.lower()))

    storage_root = STORAGE_DIR.resolve()

    for entry in entries:
        try:
            stat_info = entry.stat()
            rel_path = str(entry.resolve().relative_to(storage_root)).replace("\\", "/")
            is_dir = entry.is_dir()
            
            items.append({
                "name": entry.name,
                "path": rel_path,
                "is_dir": is_dir,
                "size": stat_info.st_size if not is_dir else 0,
                "modified": int(stat_info.st_mtime),
                "extension": entry.suffix.lower() if not is_dir else "",
                "is_text": is_text_file(entry.name) if not is_dir else False
            })
        except (OSError, ValueError):
            continue

    # Relative path calculation for UI breadcrumbs
    current_rel = ""
    parent_rel = None
    if dir_path != storage_root:
        current_rel = str(dir_path.relative_to(storage_root)).replace("\\", "/")
        parent = dir_path.parent
        if parent == storage_root or parent.is_relative_to(storage_root):
            parent_rel = str(parent.relative_to(storage_root)).replace("\\", "/")
            if parent_rel == ".":
                parent_rel = ""

    # Generate breadcrumb segments
    breadcrumbs = [{"name": "Home", "path": ""}]
    if current_rel:
        parts = current_rel.split("/")
        accum = []
        for p in parts:
            if p:
                accum.append(p)
                breadcrumbs.append({"name": p, "path": "/".join(accum)})

    return {
        "current_path": current_rel,
        "parent_path": parent_rel,
        "breadcrumbs": breadcrumbs,
        "items": items,
        "total_items": len(items)
    }

@router.post("/mkdir")
async def create_directory(data: MkdirRequest):
    """Create a new folder inside the specified parent directory."""
    parent = get_safe_path(data.parent_path, allow_root=True)
    if not parent.exists() or not parent.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent directory does not exist."
        )

    # Sanitize folder name
    clean_name = data.folder_name.strip().replace("/", "").replace("\\", "")
    if not clean_name or clean_name in (".", ".."):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid folder name."
        )

    new_dir = parent / clean_name
    if new_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A file or folder with this name already exists."
        )

    new_dir.mkdir(parents=False, exist_ok=False)
    rel = str(new_dir.resolve().relative_to(STORAGE_DIR.resolve())).replace("\\", "/")
    return {"message": "Folder created successfully.", "path": rel}

@router.post("/rename")
async def rename_item(data: RenameRequest):
    """Rename a file or directory within its current location."""
    target = get_safe_path(data.path, allow_root=False)
    if not target.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target item does not exist."
        )

    clean_name = data.new_name.strip().replace("/", "").replace("\\", "")
    if not clean_name or clean_name in (".", ".."):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid new name."
        )

    new_target = target.parent / clean_name
    if new_target.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An item with the new name already exists."
        )

    target.rename(new_target)
    rel = str(new_target.resolve().relative_to(STORAGE_DIR.resolve())).replace("\\", "/")
    return {"message": "Item renamed successfully.", "path": rel}

@router.delete("/delete")
async def delete_item(
    path: Optional[str] = Query(None, description="Path to delete"),
    data: Optional[DeleteRequest] = None
):
    """Delete a non-system file or folder inside the storage sandbox."""
    target_path = path or (data.path if data else "")
    if target_path is None:
        target_path = ""

    target = get_safe_path(target_path, allow_root=False)
    if not target.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target item does not exist."
        )

    try:
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        return {"message": f"Successfully deleted {target.name}."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete item: {str(e)}"
        )
