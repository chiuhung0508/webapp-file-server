import io
import zipfile
import mimetypes
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse, StreamingResponse
import aiofiles
from app.security import get_current_user, get_safe_path
from app.config import STORAGE_DIR

router = APIRouter(prefix="/api/transfer", tags=["transfer"], dependencies=[Depends(get_current_user)])

CHUNK_SIZE = 64 * 1024  # 64 KB streaming buffer

@router.post("/upload")
async def upload_files(
    target_folder: str = Form("", description="Target subfolder path in storage"),
    files: List[UploadFile] = File(..., description="Files to upload")
):
    """Upload one or more files into a specified target directory."""
    dest_dir = get_safe_path(target_folder, allow_root=True)

    if not dest_dir.exists():
        dest_dir.mkdir(parents=True, exist_ok=True)

    if not dest_dir.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Destination path is not a directory."
        )

    uploaded_results = []
    
    for upload in files:
        # Sanitize filename (strip directory components)
        filename = Path(upload.filename).name
        if not filename or filename in (".", ".."):
            continue

        target_file = dest_dir / filename

        # Stream file to disk in chunks to handle large files efficiently
        try:
            total_bytes = 0
            async with aiofiles.open(target_file, "wb") as out_file:
                while content := await upload.read(CHUNK_SIZE):
                    await out_file.write(content)
                    total_bytes += len(content)

            rel_path = str(target_file.resolve().relative_to(STORAGE_DIR.resolve())).replace("\\", "/")
            uploaded_results.append({
                "filename": filename,
                "path": rel_path,
                "size": total_bytes
            })
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed writing file {filename}: {str(e)}"
            )

    return {
        "message": f"Successfully uploaded {len(uploaded_results)} file(s).",
        "files": uploaded_results
    }

@router.get("/download")
async def download_file(path: str = Query(..., description="Relative file path")):
    """Download an individual file."""
    target = get_safe_path(path, allow_root=False)

    if not target.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found."
        )

    if target.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot download directory directly. Use zip download."
        )

    media_type, _ = mimetypes.guess_type(target.name)
    if not media_type:
        media_type = "application/octet-stream"

    return FileResponse(
        path=target,
        media_type=media_type,
        filename=target.name
    )

@router.get("/zip")
async def download_directory_as_zip(path: str = Query("", description="Relative folder path")):
    """Compress and stream a directory as a .zip archive."""
    target = get_safe_path(path, allow_root=True)

    if not target.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found."
        )

    if not target.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target is not a directory."
        )

    zip_filename = f"{target.name or 'storage'}.zip"

    # In-memory streaming generator for zip archive
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in target.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(target)
                zip_file.write(file_path, arcname)

    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'}
    )
