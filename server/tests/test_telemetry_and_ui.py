import pytest
from fastapi.testclient import TestClient
from server.src.main import app
from server.src.database import init_db
from server.src.api.websocket import ws_broker

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()

client = TestClient(app)

def test_dashboard_route_serves_html():
    res = client.get("/")
    assert res.status_code == 200
    assert "Playwright Orchestrator" in res.text
    assert "Enterprise Edition" in res.text
    assert "Xterm" in res.text or "xterm" in res.text

def test_websocket_log_broker_buffer():
    job_id = "test-job-buffer-999"
    msg_1 = {"type": "LOG_STREAM", "job_id": job_id, "data": "Running 3 tests\n"}
    msg_2 = {"type": "LOG_STREAM", "job_id": job_id, "data": "✓ test 1 passed\n"}

    import asyncio
    asyncio.run(ws_broker.broadcast_job_log(job_id, msg_1))
    asyncio.run(ws_broker.broadcast_job_log(job_id, msg_2))

    # Test raw text retrieval
    raw = ws_broker.get_job_raw_logs(job_id)
    assert "Running 3 tests" in raw
    assert "✓ test 1 passed" in raw

    # Test REST endpoint
    res = client.get(f"/api/v1/ws/logs/{job_id}")
    assert res.status_code == 200
    assert "Running 3 tests" in res.text
