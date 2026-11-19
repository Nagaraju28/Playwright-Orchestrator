import io
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from server.src.main import app
from server.src.database import SessionLocal, init_db
from server.src.models.project import Project, IngestionType
from server.src.models.agent import Agent, AgentStatus
from server.src.models.job import Job, JobStatus
from server.src.models.test_result import TestCaseResult, TestStatus
from server.src.services.watchdog import HeartbeatWatchdog
from server.src.services.reporter import PlaywrightReportParser
from server.src.api.websocket import ws_broker

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()

client = TestClient(app)

def test_us1_project_management_git_and_zip():
    """US-1 Acceptance Criteria: Projects support Git and Zip ingestion."""
    # 1. Create Git Project
    git_payload = {
        "name": "E2E Checkout Suite",
        "description": "Regression test suite",
        "ingestion_type": "GIT",
        "git_url": "https://github.com/corp/checkout-tests.git",
        "git_branch": "release/v2",
        "git_pat": "ghp_mockSecretToken",
    }
    res = client.post("/api/v1/projects/", json=git_payload)
    assert res.status_code == 201
    git_proj = res.json()
    assert git_proj["name"] == "E2E Checkout Suite"
    assert git_proj["git_branch"] == "release/v2"

    # 2. Upload Zip bundle to project
    zip_bytes = io.BytesIO()
    import zipfile
    with zipfile.ZipFile(zip_bytes, "w") as zf:
        zf.writestr("playwright.config.ts", "export default {};")
        zf.writestr("tests/smoke.spec.ts", "test('smoke', () => {});")
    zip_bytes.seek(0)

    upload_res = client.post(
        f"/api/v1/projects/{git_proj['id']}/upload-bundle",
        files={"file": ("suite.zip", zip_bytes, "application/zip")},
    )
    assert upload_res.status_code == 200
    assert upload_res.json()["files_extracted"] == 2

def test_us2_job_execution_and_dispatch():
    """US-2 Acceptance Criteria: Control Plane queues and dispatches execution requests."""
    # 1. Register agent
    agent_res = client.post("/api/v1/agents/register", json={
        "name": "e2e-worker-node",
        "hostname": "win-e2e-vm",
        "platform": "win32",
    })
    assert agent_res.status_code == 201
    agent_id = agent_res.json()["id"]

    # 2. Create project
    proj_res = client.post("/api/v1/projects/", json={"name": "Dispatch Test Project"})
    proj_id = proj_res.json()["id"]

    # 3. Trigger Job Run
    job_res = client.post("/api/v1/jobs/trigger", json={
        "project_id": proj_id,
        "environment": "staging",
        "target_tags": "@smoke",
        "cli_arguments": "--workers=1",
    })
    assert job_res.status_code == 201
    job = job_res.json()
    assert job["status"] in (JobStatus.QUEUED, JobStatus.DISPATCHED, JobStatus.RUNNING)

def test_us3_realtime_websocket_telemetry():
    """US-3 Acceptance Criteria: Agent streams logs, client receives in real-time (<500ms latency)."""
    job_id = "test-ws-e2e-job-123"

    import asyncio
    asyncio.run(ws_broker.broadcast_job_log(job_id, {
        "type": "LOG_STREAM",
        "job_id": job_id,
        "data": "Running 2 tests using 1 worker\n",
    }))

    # Verify log was buffered and retrievable via REST
    res = client.get(f"/api/v1/ws/logs/{job_id}")
    assert res.status_code == 200
    assert "Running 2 tests" in res.text

def test_us4_metrics_artifacts_and_watchdog_orphan_recovery():
    """US-4 Acceptance Criteria: Playwright JSON reports, artifacts, and NFR-4 orphaned VM recovery."""
    db = SessionLocal()
    try:
        # Create project and job
        project = Project(name="Metrics Project")
        db.add(project)
        db.commit()

        job = Job(project_id=project.id, status=JobStatus.RUNNING)
        db.add(job)
        db.commit()

        # 1. Upload Artifact (Screenshot)
        png_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        art_res = client.post(
            f"/api/v1/artifacts/upload/{job.id}",
            files={"file": ("failure_login.png", io.BytesIO(png_data), "image/png")},
        )
        assert art_res.status_code == 200
        screenshot_url = art_res.json()["url"]

        # 2. Ingest Playwright JSON Report
        sample_report = {
            "stats": {"duration": 3420},
            "suites": [
                {
                    "title": "auth.spec.ts",
                    "file": "tests/auth.spec.ts",
                    "specs": [
                        {
                            "title": "valid user login",
                            "tests": [{
                                "status": "expected",
                                "results": [{"status": "passed", "duration": 1200}],
                            }],
                        },
                        {
                            "title": "invalid password error",
                            "tests": [{
                                "status": "unexpected",
                                "results": [{
                                    "status": "failed",
                                    "duration": 2220,
                                    "error": {"message": "Expected error banner to be visible"},
                                    "attachments": [{"name": "screenshot", "path": screenshot_url}],
                                }],
                            }],
                        },
                    ],
                }
            ],
        }

        report_res = client.post(f"/api/v1/jobs/{job.id}/results", json=sample_report)
        assert report_res.status_code == 200
        summary = report_res.json()["summary"]
        assert summary["total_tests"] == 2
        assert summary["passed"] == 1
        assert summary["failed"] == 1

        # 3. Test Invariant NFR-4: Heartbeat Watchdog Orphan Recovery
        stale_agent = Agent(
            name="crashing-vm-node",
            hostname="worker-crash-01",
            auth_token="agt_crashing_token_999",
            status=AgentStatus.BUSY,
            current_job_id=job.id,
            # Heartbeat is 60 seconds old
            last_heartbeat=datetime.utcnow() - timedelta(seconds=60),
        )
        db.add(stale_agent)
        job.status = JobStatus.RUNNING
        job.agent_id = stale_agent.id
        db.commit()

        # Run Watchdog Check
        events = HeartbeatWatchdog.check_agent_heartbeats(db, timeout_seconds=30)
        assert len(events) >= 1
        assert any(ev["job_id"] == job.id for ev in events)

        # Confirm job transitioned to ORPHANED per NFR-4
        db.refresh(job)
        assert job.status == JobStatus.ORPHANED
        assert "disconnected mid-execution" in job.error_summary
        assert "Invariant NFR-4" in job.error_summary
    finally:
        db.close()
