import asyncio
import json
from collections import deque
from datetime import datetime
from typing import Dict, Set, Deque
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import PlainTextResponse
from ..database import SessionLocal
from ..models.job import Job, JobStatus
from ..models.agent import Agent, AgentStatus

router = APIRouter(prefix="/ws", tags=["Telemetry"])

class WebSocketLogBroker:
    """Pub/Sub broker routing live stdout/stderr test streams from Agents to UI clients with replay buffer."""

    def __init__(self, buffer_size: int = 2000):
        self.buffer_size = buffer_size
        # job_id -> set of UI client WebSockets
        self.active_ui_subscribers: Dict[str, Set[WebSocket]] = {}
        # agent_id -> WebSocket connection
        self.active_agent_connections: Dict[str, WebSocket] = {}
        # job_id -> Deque of buffered log messages
        self.job_log_buffers: Dict[str, Deque[dict]] = {}

    async def connect_ui(self, job_id: str, websocket: WebSocket):
        await websocket.accept()
        if job_id not in self.active_ui_subscribers:
            self.active_ui_subscribers[job_id] = set()
        self.active_ui_subscribers[job_id].add(websocket)

        # Immediate replay of buffered logs for this job (<500ms latency)
        if job_id in self.job_log_buffers:
            for entry in list(self.job_log_buffers[job_id]):
                try:
                    await websocket.send_text(json.dumps(entry))
                except Exception:
                    break

    def disconnect_ui(self, job_id: str, websocket: WebSocket):
        if job_id in self.active_ui_subscribers:
            self.active_ui_subscribers[job_id].discard(websocket)
            if not self.active_ui_subscribers[job_id]:
                del self.active_ui_subscribers[job_id]

    async def broadcast_job_log(self, job_id: str, message: dict):
        """Append to ring buffer and broadcast to UI clients in real-time."""
        # Save in buffer
        if job_id not in self.job_log_buffers:
            self.job_log_buffers[job_id] = deque(maxlen=self.buffer_size)
        self.job_log_buffers[job_id].append(message)

        if job_id in self.active_ui_subscribers:
            payload = json.dumps(message)
            dead_sockets = set()
            for ws in self.active_ui_subscribers[job_id]:
                try:
                    await ws.send_text(payload)
                except Exception:
                    dead_sockets.add(ws)
            for dead in dead_sockets:
                self.disconnect_ui(job_id, dead)

    def get_job_raw_logs(self, job_id: str) -> str:
        """Fetch concatenated logs as plaintext."""
        if job_id not in self.job_log_buffers:
            return ""
        return "".join(entry.get("data", "") for entry in self.job_log_buffers[job_id])

ws_broker = WebSocketLogBroker()

@router.websocket("/agent/{agent_id}")
async def agent_telemetry_ws(websocket: WebSocket, agent_id: str):
    """WebSocket endpoint where Agent Daemon connects to stream live logs & heartbeat."""
    await websocket.accept()
    ws_broker.active_agent_connections[agent_id] = websocket

    # Auto-dispatch any queued jobs when a worker connects
    db = SessionLocal()
    try:
        from ..services.dispatcher import JobDispatcher
        await JobDispatcher.dispatch_next_job(db)
    except Exception:
        pass
    finally:
        db.close()

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                job_id = msg.get("job_id")
                msg_type = msg.get("type")

                # Handle raw log streaming
                if job_id and msg_type == "LOG_STREAM":
                    await ws_broker.broadcast_job_log(job_id, msg)
                
                # Handle test execution completion notification
                elif job_id and msg_type == "JOB_EXECUTION_FINISHED":
                    await handle_job_finished(msg)
                    await ws_broker.broadcast_job_log(job_id, msg)

            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        if agent_id in ws_broker.active_agent_connections:
            del ws_broker.active_agent_connections[agent_id]

async def handle_job_finished(payload: dict):
    """Update job and agent status in database when execution terminates."""
    job_id = payload.get("job_id")
    exit_code = payload.get("exit_code", 1)
    duration_ms = payload.get("duration_ms", 0)

    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = JobStatus.COMPLETED if exit_code == 0 else JobStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.execution_duration_ms = duration_ms
            if exit_code != 0:
                job.error_summary = f"Playwright process exited with code {exit_code}"

            # Free up agent
            if job.agent_id:
                agent = db.query(Agent).filter(Agent.id == job.agent_id).first()
                if agent:
                    agent.status = AgentStatus.IDLE
                    agent.current_job_id = None
            db.commit()

            # Automatically dispatch next queued job if available
            try:
                from ..services.dispatcher import JobDispatcher
                await JobDispatcher.dispatch_next_job(db)
            except Exception:
                pass
    finally:
        db.close()

@router.websocket("/logs/{job_id}")
async def ui_job_logs_ws(websocket: WebSocket, job_id: str):
    """WebSocket endpoint where Frontend Dashboard connects to stream Xterm logs."""
    await ws_broker.connect_ui(job_id, websocket)
    try:
        while True:
            # Client heartbeat
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_broker.disconnect_ui(job_id, websocket)

@router.get("/logs/{job_id}", response_class=PlainTextResponse)
def get_job_logs_text(job_id: str):
    """Retrieve full execution log buffer as plaintext for download or offline review."""
    return ws_broker.get_job_raw_logs(job_id)
