import asyncio
import json
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from ..models.agent import Agent, AgentStatus
from ..models.job import Job, JobStatus
from ..models.project import Project
from ..api.websocket import ws_broker

class JobDispatcher:
    """Orchestrates job queues, agent worker registries, and task dispatching."""

    @staticmethod
    def get_available_agents(db: Session) -> List[Agent]:
        """Fetch online, healthy worker agents currently in IDLE status."""
        agents = db.query(Agent).filter(Agent.status == AgentStatus.IDLE).all()
        return [a for a in agents if a.is_healthy(timeout_seconds=30)]

    @classmethod
    async def dispatch_next_job(cls, db: Session) -> Optional[Job]:
        """Find the oldest queued job and dispatch to an available agent."""
        queued_job = (
            db.query(Job)
            .filter(Job.status == JobStatus.QUEUED)
            .order_by(Job.created_at.asc())
            .first()
        )
        if not queued_job:
            return None

        available_agents = cls.get_available_agents(db)
        if not available_agents:
            return None  # No workers ready; job remains QUEUED

        target_agent = available_agents[0]
        project = db.query(Project).filter(Project.id == queued_job.project_id).first()
        if not project:
            queued_job.status = JobStatus.FAILED
            queued_job.error_summary = f"Project '{queued_job.project_id}' not found."
            db.commit()
            return queued_job

        # State transition
        queued_job.status = JobStatus.DISPATCHED
        queued_job.agent_id = target_agent.id
        queued_job.started_at = datetime.utcnow()

        target_agent.status = AgentStatus.BUSY
        target_agent.current_job_id = queued_job.id
        db.commit()

        # Build payload for agent daemon
        dispatch_payload = {
            "type": "EXECUTE_JOB",
            "job_id": queued_job.id,
            "project": {
                "id": project.id,
                "name": project.name,
                "ingestion_type": project.ingestion_type.value,
                "git_url": project.git_url,
                "git_branch": project.git_branch or "main",
                "git_pat": project.git_pat_encrypted,
                "zip_storage_path": project.zip_storage_path,
            },
            "environment": queued_job.environment,
            "target_tags": queued_job.target_tags,
            "cli_arguments": queued_job.cli_arguments,
        }

        # Deliver dispatch command via active WebSocket connection
        agent_ws = ws_broker.active_agent_connections.get(target_agent.id)
        if agent_ws:
            try:
                await agent_ws.send_text(json.dumps(dispatch_payload))
                queued_job.status = JobStatus.RUNNING
                db.commit()
            except Exception as e:
                # WebSocket delivery error, revert state
                queued_job.status = JobStatus.FAILED
                queued_job.error_summary = f"Failed to deliver job to agent WS: {str(e)}"
                target_agent.status = AgentStatus.IDLE
                target_agent.current_job_id = None
                db.commit()

        return queued_job
