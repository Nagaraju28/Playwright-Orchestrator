import pytest
from pathlib import Path
from server.src.database import SessionLocal, init_db
from server.src.models.project import Project, IngestionType
from server.src.models.agent import Agent, AgentStatus
from server.src.models.job import Job, JobStatus
from server.src.services.ingestion import IngestionService
from server.src.services.dispatcher import JobDispatcher
import zipfile

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()

def test_git_pat_url_formatting():
    raw_url = "https://github.com/my-org/my-playwright-tests.git"
    pat = "ghp_secureToken12345"
    auth_url = IngestionService.format_authenticated_git_url(raw_url, pat)
    assert f"oauth2:{pat}@github.com" in auth_url
    assert "my-playwright-tests.git" in auth_url

def test_zip_bundle_extraction(tmp_path: Path):
    # Create sample zip file
    zip_path = tmp_path / "test_bundle.zip"
    extract_target = tmp_path / "extracted_workspace"

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("playwright.config.js", "// Playwright config")
        zf.writestr("tests/login.spec.js", "test('login', () => {});")

    count = IngestionService.extract_zip_bundle(zip_path, extract_target)
    assert count == 2
    assert (extract_target / "playwright.config.js").exists()
    assert (extract_target / "tests/login.spec.js").exists()

@pytest.mark.asyncio
async def test_job_dispatcher_queue_selection():
    db = SessionLocal()
    try:
        # Create test project
        project = Project(name="Dispatcher Test Project", git_url="https://github.com/test/repo.git")
        db.add(project)
        db.commit()

        # Create healthy idle agent
        agent = Agent(
            name="dispatcher-agent-01",
            hostname="worker-node-1",
            auth_token="agt_dispatcher_tok_123",
            status=AgentStatus.IDLE,
        )
        db.add(agent)
        db.commit()

        # Create queued job
        job = Job(
            project_id=project.id,
            environment="staging",
            status=JobStatus.QUEUED,
        )
        db.add(job)
        db.commit()

        # Available agents query
        available = JobDispatcher.get_available_agents(db)
        assert len(available) >= 1
        assert any(a.name == "dispatcher-agent-01" for a in available)

        # Dispatch next job
        dispatched = await JobDispatcher.dispatch_next_job(db)
        assert dispatched is not None
        assert dispatched.id == job.id
        assert dispatched.agent_id == agent.id
        # State transitioned to DISPATCHED
        assert dispatched.status in (JobStatus.DISPATCHED, JobStatus.RUNNING)
    finally:
        db.close()
