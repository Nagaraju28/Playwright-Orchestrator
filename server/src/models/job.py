import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, JSON, Integer
from sqlalchemy.orm import relationship
import enum
from ..database import Base

class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    DISPATCHED = "DISPATCHED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ORPHANED = "ORPHANED"  # Invariant NFR-4: Disconnected mid-run

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=True, index=True)

    status = Column(Enum(JobStatus), default=JobStatus.QUEUED, nullable=False, index=True)
    environment = Column(String(64), default="production", nullable=False)
    target_tags = Column(String(256), nullable=True)  # e.g. "@smoke, @regression"
    cli_arguments = Column(String(512), nullable=True) # e.g. "--workers=2 --headed"

    # Execution telemetry & summary metrics
    total_tests = Column(Integer, default=0)
    passed_tests = Column(Integer, default=0)
    failed_tests = Column(Integer, default=0)
    skipped_tests = Column(Integer, default=0)
    execution_duration_ms = Column(Integer, default=0)
    
    error_summary = Column(String(1024), nullable=True)
    meta_info = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    project = relationship("Project", backref="jobs")
    agent = relationship("Agent", backref="jobs")

    def __repr__(self) -> str:
        return f"<Job {self.id} [{self.status}] on Project {self.project_id}>"
