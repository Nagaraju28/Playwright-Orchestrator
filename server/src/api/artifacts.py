import os
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from ..config import BASE_DIR

router = APIRouter(prefix="/artifacts", tags=["Artifacts"])

ARTIFACTS_DIR = Path(BASE_DIR) / "storage" / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/upload/{job_id}")
async def upload_artifact(job_id: str, file: UploadFile = File(...)):
    """Upload test failure artifacts (screenshots, videos, traces) to storage (FR-4.3)."""
    job_dir = ARTIFACTS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize filename
    safe_filename = Path(file.filename).name
    dest_path = job_dir / safe_filename

    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    artifact_url = f"/api/v1/artifacts/{job_id}/{safe_filename}"
    return {
        "status": "uploaded",
        "job_id": job_id,
        "filename": safe_filename,
        "url": artifact_url,
        "size_bytes": dest_path.stat().st_size,
    }

@router.get("/{job_id}/{filename}")
def retrieve_artifact(job_id: str, filename: str):
    """Retrieve test artifact file (image/png, video/webm, application/zip)."""
    file_path = ARTIFACTS_DIR / job_id / Path(filename).name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Artifact not found")

    media_type = "application/octet-stream"
    if filename.endswith(".png"):
        media_type = "image/png"
    elif filename.endswith(".webm"):
        media_type = "video/webm"
    elif filename.endswith(".zip"):
        media_type = "application/zip"

    return FileResponse(file_path, media_type=media_type)
