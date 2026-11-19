import pytest
import uuid
from fastapi.testclient import TestClient
from server.src.main import app
from server.src.database import init_db

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()

client = TestClient(app)

def test_health_check():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"

def test_project_crud():
    uid = uuid.uuid4().hex[:6]
    payload = {
        "name": f"Playwright Demo Project {uid}",
        "description": "Integration test suite for e-commerce checkout",
        "ingestion_type": "GIT",
        "git_url": "https://github.com/example/e2e-tests.git",
        "git_branch": "main",
    }
    res = client.post("/api/v1/projects/", json=payload)
    assert res.status_code == 201
    created = res.json()
    assert created["name"] == payload["name"]
    project_id = created["id"]

    # List projects
    res_list = client.get("/api/v1/projects/")
    assert res_list.status_code == 200
    ids = [p["id"] for p in res_list.json()]
    assert project_id in ids

def test_agent_registration():
    uid = uuid.uuid4().hex[:6]
    payload = {
        "name": f"worker-vm-{uid}",
        "hostname": "win-agent-srv.corp.local",
        "ip_address": "10.0.1.45",
        "platform": "win32",
        "max_concurrent_jobs": 2,
    }
    res = client.post("/api/v1/agents/register", json=payload)
    assert res.status_code == 201
    agent = res.json()
    assert agent["name"] == payload["name"]
    assert "auth_token" in agent
    assert agent["status"] == "IDLE"

def test_job_trigger():
    uid = uuid.uuid4().hex[:6]
    # Create project first
    proj_res = client.post("/api/v1/projects/", json={"name": f"Job Trigger Project {uid}"})
    proj_id = proj_res.json()["id"]

    job_payload = {
        "project_id": proj_id,
        "environment": "staging",
        "target_tags": "@smoke",
        "cli_arguments": "--workers=2",
    }
    res = client.post("/api/v1/jobs/trigger", json=job_payload)
    assert res.status_code == 201
    job = res.json()
    assert job["status"] in ("QUEUED", "DISPATCHED", "RUNNING")
    assert job["project_id"] == proj_id
