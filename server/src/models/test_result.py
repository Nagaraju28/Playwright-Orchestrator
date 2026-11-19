import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Integer, Text, JSON
from sqlalchemy.orm import relationship
import enum
from ..database import Base

class TestStatus(str, enum.Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    TIMED_OUT = "TIMED_OUT"

class TestCaseResult(Base):
    __tablename__ = "test_case_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(36), ForeignKey("jobs.id"), nullable=False, index=True)

    suite_name = Column(String(256), nullable=False)
    test_title = Column(String(512), nullable=False)
    file_path = Column(String(512), nullable=False)
    
    status = Column(Enum(TestStatus), nullable=False, index=True)
    duration_ms = Column(Integer, default=0)
    retry_count = Column(Integer, default=0)
    
    error_message = Column(Text, nullable=True)
    error_stacktrace = Column(Text, nullable=True)

    # S3 / MinIO artifact links (Screenshots, Playwright trace.zip, video.webm)
    screenshot_url = Column(String(1024), nullable=True)
    trace_url = Column(String(1024), nullable=True)
    video_url = Column(String(1024), nullable=True)
    extra_artifacts = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    job = relationship("Job", backref="test_results")

    def __repr__(self) -> str:
        return f"<TestCaseResult {self.test_title} [{self.status}]>"
