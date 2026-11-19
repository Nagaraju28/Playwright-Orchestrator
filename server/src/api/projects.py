from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from pathlib import Path
import shutil
from ..database import get_db
from ..models.project import Project, IngestionType
from ..schemas.project import ProjectCreate, ProjectResponse
from ..services.ingestion import IngestionService
from ..config import BASE_DIR

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new Playwright test project (FR-1.1)."""
    existing = db.query(Project).filter(Project.name == payload.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Project with name '{payload.name}' already exists",
        )
    
    project = Project(
        name=payload.name,
        description=payload.description,
        ingestion_type=payload.ingestion_type,
        git_url=payload.git_url,
        git_branch=payload.git_branch or "main",
        git_pat_encrypted=payload.git_pat, # In production encrypt with AES-GCM
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project

@router.get("/", response_model=List[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    """List all registered projects."""
    return db.query(Project).order_by(Project.created_at.desc()).all()

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)):
    """Retrieve details for a single project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.post("/{project_id}/upload-bundle")
async def upload_project_zip_bundle(
    project_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload and extract a zipped Playwright workspace bundle (FR-1.2)."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Uploaded bundle must be a .zip file")

    storage_dir = Path(BASE_DIR) / "storage" / "bundles" / project_id
    storage_dir.mkdir(parents=True, exist_ok=True)
    zip_path = storage_dir / file.filename

    with open(zip_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Extract to target directory
    extract_dir = storage_dir / "unpacked"
    count = IngestionService.extract_zip_bundle(zip_path, extract_dir)

    project.ingestion_type = IngestionType.ZIP
    project.zip_storage_path = str(zip_path)
    db.commit()

    return {
        "status": "success",
        "project_id": project_id,
        "files_extracted": count,
        "storage_path": str(zip_path),
    }
