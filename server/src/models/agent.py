import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum, Integer, JSON
import enum
from ..database import Base

class AgentStatus(str, enum.Enum):
    IDLE = "IDLE"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"

class Agent(Base):
    __tablename__ = "agents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(128), unique=True, nullable=False, index=True)
    hostname = Column(String(256), nullable=False)
    ip_address = Column(String(64), nullable=True)
    platform = Column(String(64), nullable=True)  # win32, linux, darwin
    
    status = Column(Enum(AgentStatus), default=AgentStatus.IDLE, nullable=False, index=True)
    auth_token = Column(String(256), nullable=False, unique=True, index=True)
    
    current_job_id = Column(String(36), nullable=True)
    max_concurrent_jobs = Column(Integer, default=1, nullable=False)
    system_metrics = Column(JSON, nullable=True)  # cpu, mem, disk free

    last_heartbeat = Column(DateTime, default=datetime.utcnow, nullable=False)
    registered_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    @property
    def is_healthy(self) -> bool:
        """Evaluate if the agent is considered alive based on heartbeat interval."""
        if not self.last_heartbeat:
            return False
        delta = (datetime.utcnow() - self.last_heartbeat).total_seconds()
        return delta <= 30

    def __repr__(self) -> str:
        return f"<Agent {self.name} [{self.status}] ({self.id})>"
