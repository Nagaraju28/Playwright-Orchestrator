import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models.agent import Agent, AgentStatus
from ..models.job import Job, JobStatus
from ..api.websocket import ws_broker

class HeartbeatWatchdog:
    """Monitors worker VM heartbeats and enforces Invariant NFR-4 (Orphaned Job Recovery)."""

    @classmethod
    def check_agent_heartbeats(cls, db: Session, timeout_seconds: int = 30) -> List[dict]:
        """Scan agents for heartbeat timeouts and gracefully mark mid-execution jobs as ORPHANED."""
        cutoff = datetime.utcnow() - timedelta(seconds=timeout_seconds)
        orphaned_events = []

        # Find agents whose heartbeats have expired and are not already marked OFFLINE
        stale_agents = (
            db.query(Agent)
            .filter(Agent.last_heartbeat < cutoff, Agent.status != AgentStatus.OFFLINE)
            .all()
        )

        for agent in stale_agents:
            old_status = agent.status
            agent.status = AgentStatus.OFFLINE

            # Check if agent was executing a job
            if agent.current_job_id:
                job = db.query(Job).filter(Job.id == agent.current_job_id).first()
                if job and job.status in (JobStatus.RUNNING, JobStatus.DISPATCHED):
                    job.status = JobStatus.ORPHANED
                    job.completed_at = datetime.utcnow()
                    job.error_summary = (
                        f"Agent VM '{agent.name}' disconnected mid-execution. "
                        f"No heartbeat received in > {timeout_seconds}s. (Invariant NFR-4 Enforcement)"
                    )
                    orphaned_events.append({
                        "job_id": job.id,
                        "agent_id": agent.id,
                        "agent_name": agent.name,
                        "reason": job.error_summary,
                    })

            agent.current_job_id = None

        if stale_agents:
            db.commit()

        return orphaned_events

    @classmethod
    async def run_periodic_watchdog(cls, interval_seconds: int = 10, timeout_seconds: int = 30):
        """Asynchronous background loop running throughout the application lifespan."""
        while True:
            try:
                db = SessionLocal()
                try:
                    events = cls.check_agent_heartbeats(db, timeout_seconds=timeout_seconds)
                    for ev in events:
                        # Broadcast notification to dashboard clients
                        await ws_broker.broadcast_job_log(
                            ev["job_id"],
                            {
                                "type": "JOB_ORPHANED",
                                "job_id": ev["job_id"],
                                "agent_id": ev["agent_id"],
                                "error": ev["reason"],
                                "data": f"\r\n\x1b[1;31m[NFR-4 WATCHDOG ALERT] {ev['reason']}\x1b[0m\r\n",
                            },
                        )
                finally:
                    db.close()
            except Exception:
                pass
            await asyncio.sleep(interval_seconds)
