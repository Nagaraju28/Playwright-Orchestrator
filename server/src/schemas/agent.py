from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from ..models.agent import AgentStatus

class AgentRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    hostname: str = Field(..., max_length=256)
    ip_address: Optional[str] = None
    platform: Optional[str] = "unknown"
    max_concurrent_jobs: int = Field(default=1, ge=1, le=10)

class AgentHeartbeat(BaseModel):
    agent_id: str
    status: AgentStatus
    current_job_id: Optional[str] = None
    system_metrics: Optional[Dict[str, Any]] = None

class AgentResponse(BaseModel):
    id: str
    name: str
    hostname: str
    ip_address: Optional[str]
    platform: Optional[str]
    status: AgentStatus
    auth_token: str
    last_heartbeat: datetime
    registered_at: datetime
    is_healthy: bool = True

    class Config:
        from_attributes = True
