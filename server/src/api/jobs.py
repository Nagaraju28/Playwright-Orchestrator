from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models.project import Project
from ..models.job import Job, JobStatus
from ..models.test_result import TestCaseResult
from ..schemas.job import JobCreate, JobResponse
from ..services.dispatcher import JobDispatcher
from ..services.reporter import PlaywrightReportParser
from typing import Dict, Any

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.post("/trigger", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def trigger_job(payload: JobCreate, db: Session = Depends(get_db)):
    """Trigger a new test execution run and queue it for dispatch (FR-2.1)."""
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target project '{payload.project_id}' does not exist",
        )
    
    job = Job(
        project_id=payload.project_id,
        environment=payload.environment,
        target_tags=payload.target_tags,
        cli_arguments=payload.cli_arguments,
        status=JobStatus.QUEUED,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Attempt immediate dispatch if an agent is ready
    await JobDispatcher.dispatch_next_job(db)
    db.refresh(job)

    return job

@router.post("/dispatch-pending")
async def dispatch_pending_jobs(db: Session = Depends(get_db)):
    """Manually invoke dispatcher cycle to drain queued jobs."""
    dispatched = await JobDispatcher.dispatch_next_job(db)
    if dispatched:
        return {"status": "dispatched", "job_id": dispatched.id, "agent_id": dispatched.agent_id}
    return {"status": "idle", "message": "No queued jobs or no available agents"}

@router.get("/", response_model=List[JobResponse])
def list_jobs(project_id: str = None, db: Session = Depends(get_db)):
    """List execution jobs, optionally filtered by project."""
    query = db.query(Job)
    if project_id:
        query = query.filter(Job.project_id == project_id)
    return query.order_by(Job.created_at.desc()).limit(100).all()

@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Retrieve details and metrics of an execution job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/{job_id}/results")
def upload_job_results(job_id: str, report_payload: Dict[str, Any], db: Session = Depends(get_db)):
    """Upload and parse Playwright JSON results, aggregating metrics (FR-4.1)."""
    try:
        summary = PlaywrightReportParser.parse_and_persist(db, job_id, report_payload)
        return {"status": "success", "summary": summary}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{job_id}/results")
def get_job_results(job_id: str, db: Session = Depends(get_db)):
    """Fetch structured test case outcomes with stacktraces and artifact links (FR-4.2)."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    test_cases = db.query(TestCaseResult).filter(TestCaseResult.job_id == job_id).all()
    return {
        "job_id": job.id,
        "summary": {
            "status": job.status,
            "total": job.total_tests,
            "passed": job.passed_tests,
            "failed": job.failed_tests,
            "skipped": job.skipped_tests,
            "duration_ms": job.execution_duration_ms,
        },
        "test_cases": [
            {
                "id": tc.id,
                "suite": tc.suite_name,
                "title": tc.test_title,
                "status": tc.status,
                "duration_ms": tc.duration_ms,
                "error_message": tc.error_message,
                "screenshot_url": tc.screenshot_url,
                "trace_url": tc.trace_url,
                "video_url": tc.video_url,
            }
            for tc in test_cases
        ],
    }
