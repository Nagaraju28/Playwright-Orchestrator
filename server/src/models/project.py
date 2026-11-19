import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Enum
import enum
from ..database import Base

class IngestionType(str, enum.Enum):
    GIT = "GIT"
    ZIP = "ZIP"

class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(128), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    ingestion_type = Column(Enum(IngestionType), default=IngestionType.GIT, nullable=False)
    
    # Git integration fields (FR-1.2, FR-1.3)
    git_url = Column(String(512), nullable=True)
    git_branch = Column(String(128), default="main", nullable=True)
    git_pat_encrypted = Column(String(512), nullable=True)

    # Direct zip artifact location
    zip_storage_path = Column(String(512), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<Project {self.name} ({self.id})>"
