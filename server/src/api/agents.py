from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models.agent import Agent, AgentStatus
from ..schemas.agent import AgentRegister, AgentHeartbeat, AgentResponse
from ..auth import generate_secure_token

router = APIRouter(prefix="/agents", tags=["Agents"])

@router.post("/register", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def register_agent(payload: AgentRegister, db: Session = Depends(get_db)):
    """Register a new VM worker agent daemon (FR-2.2)."""
    agent = db.query(Agent).filter(Agent.name == payload.name).first()
    if agent:
        # Re-registering existing agent node
        agent.hostname = payload.hostname
        agent.ip_address = payload.ip_address
        agent.platform = payload.platform
        agent.status = AgentStatus.IDLE
        agent.last_heartbeat = datetime.utcnow()
    else:
        auth_token = generate_secure_token(prefix="agt_live_")
        agent = Agent(
            name=payload.name,
            hostname=payload.hostname,
            ip_address=payload.ip_address,
            platform=payload.platform,
            max_concurrent_jobs=payload.max_concurrent_jobs,
            status=AgentStatus.IDLE,
            auth_token=auth_token,
            last_heartbeat=datetime.utcnow(),
        )
        db.add(agent)
    
    db.commit()
    db.refresh(agent)
    return agent

@router.post("/heartbeat")
def record_heartbeat(payload: AgentHeartbeat, db: Session = Depends(get_db)):
    """Record live heartbeat telemetry from an active Agent VM (NFR-4)."""
    agent = db.query(Agent).filter(Agent.id == payload.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent.last_heartbeat = datetime.utcnow()
    agent.status = payload.status
    agent.current_job_id = payload.current_job_id
    if payload.system_metrics:
        agent.system_metrics = payload.system_metrics
    
    db.commit()
    return {"status": "acknowledged", "timestamp": agent.last_heartbeat.isoformat()}

@router.get("/", response_model=List[AgentResponse])
def list_agents(db: Session = Depends(get_db)):
    """List all registered execution agents with live health status."""
    return db.query(Agent).order_by(Agent.registered_at.desc()).all()

@router.post("/watchdog/check")
def trigger_watchdog_check(timeout_seconds: int = 30, db: Session = Depends(get_db)):
    """Run watchdog check manually to detect disconnected VMs and orphan jobs (NFR-4)."""
    from ..services.watchdog import HeartbeatWatchdog
    events = HeartbeatWatchdog.check_agent_heartbeats(db, timeout_seconds=timeout_seconds)
    return {"status": "ok", "orphaned_jobs_count": len(events), "events": events}
