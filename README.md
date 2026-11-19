# Enterprise Playwright Test Orchestrator

A distributed test orchestration platform for enterprise Playwright automation suites, built using **Project Brain Spec-Driven Development (SDD)**.

---

## Architecture Overview

```
                      ┌────────────────────────────────────────┐
                      │    Enterprise Web Dashboard (UI)       │
                      │  (Projects, Fleet, Real-Time Xterm.js) │
                      └───────────────────▲────────────────────┘
                                          │ HTTP / WebSockets
                                          ▼
                      ┌────────────────────────────────────────┐
                      │     Control Plane API (FastAPI)        │
                      │  - Job Dispatcher & Worker Registry    │
                      │  - Heartbeat Watchdog (NFR-4 Invariant)│
                      │  - Telemetry Replay Broker (<500ms)    │
                      └───────────────────▲────────────────────┘
                                          │ WebSockets (TLS)
                                          ▼
                 ┌──────────────────────────────────────────────────┐
                 │          Execution Plane (Agent Daemon)          │
                 │  - Target Worker VM (Windows / Linux)            │
                 │  - Workspace Isolation & Ingestion (Git/Zip)     │
                 │  - `npx playwright test` Streaming Harness       │
                 │  - Failure Artifact Uploader (Screenshots/Traces)│
                 └──────────────────────────────────────────────────┘
```

---

## Key Features & Invariants

1. **Two Ingestion Modes (FR-1)**:
   * **Git Integration**: Ingests repositories with custom branch selection and secure Personal Access Token (PAT) masking.
   * **Zip Bundle Upload**: Upload `.zip` test bundles directly to project workspaces with Zip-Slip path traversal protection.
2. **Deterministic Job Dispatcher (FR-2)**:
   * Evaluates worker pool health in real-time, atomically transitioning queued jobs to available idle agents.
3. **Sub-500ms Live Telemetry (NFR-1 / FR-3)**:
   * High-speed WebSocket log broker streaming live stdout/stderr into an interactive **Xterm.js** terminal emulator with ring-buffer replay.
4. **Heartbeat Watchdog & Orphan Recovery (NFR-4)**:
   * Enforces system invariant: If an execution agent VM disconnects mid-flight, the Control Plane immediately catches the timeout, marks the job as `ORPHANED`, and alerts the dashboard gracefully.
5. **Detailed Metrics & Artifact Storage (FR-4)**:
   * Automatically parses Playwright JSON test reports, indexes per-test run durations and stack traces, and uploads failure screenshots and Playwright traces.

---

## Quickstart Guide

> [!TIP]
> For a complete step-by-step installation guide on new systems or remote execution VMs, see 📖 **[SETUP_GUIDE.md](SETUP_GUIDE.md)**.

### 1. Start the Control Plane Server (FastAPI)
```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1 | Linux/macOS: source .venv/bin/activate
pip install -r server/requirements.txt
python -m uvicorn server.src.main:app --host 0.0.0.0 --port 8000 --reload
```
* **Interactive Web Dashboard**: Open [http://localhost:8000/](http://localhost:8000/) in your browser.
* **OpenAPI / Swagger Docs**: Available at [http://localhost:8000/docs](http://localhost:8000/docs).

### 2. Launch the Execution Agent Daemon (Node.js)
In a second terminal window on the target test execution machine:
```bash
cd agent
npm install
npx playwright install chromium
npm start
```
The agent daemon will automatically register itself with the Control Plane, initiate live heartbeat telemetry, and wait for dispatched test suites.

### 3. Run Automated Tests
```bash
# Windows PowerShell
$env:PYTHONPATH = "."
pytest server/tests/ -v
```

---

## Spec-Driven Development (SDD) Verification

This platform was developed and validated using the 3-phase Brain SDD engine:
* 📋 [requirements.md](file:///.brain/specs/orchestrator-core/requirements.md): 4 User Stories with Gherkin acceptance criteria.
* 🏗️ [design.md](file:///.brain/specs/orchestrator-core/design.md): System architecture, sequence flows, and runtime invariants.
* 🎯 [tasks.md](file:///.brain/specs/orchestrator-core/tasks.md): 13 tasks across 4 waves completed (100%).
