from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from ..models.project import IngestionType

class ProjectBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    description: Optional[str] = None
    ingestion_type: IngestionType = IngestionType.GIT
    git_url: Optional[str] = None
    git_branch: Optional[str] = "main"

class ProjectCreate(ProjectBase):
    git_pat: Optional[str] = None

class ProjectResponse(ProjectBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
