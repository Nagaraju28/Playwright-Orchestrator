from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from ..models.job import JobStatus

class JobCreate(BaseModel):
    project_id: str
    environment: str = Field(default="staging", max_length=64)
    target_tags: Optional[str] = None
    cli_arguments: Optional[str] = None

class JobResponse(BaseModel):
    id: str
    project_id: str
    agent_id: Optional[str]
    status: JobStatus
    environment: str
    target_tags: Optional[str]
    cli_arguments: Optional[str]
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    execution_duration_ms: int
    error_summary: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True
