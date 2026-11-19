# End-to-End Setup & Deployment Guide for New Systems / Agents

This guide provides complete, step-by-step instructions to clone, set up, and run the **Enterprise Playwright Test Orchestrator** on any new computer (Windows, macOS, or Linux).

---

## 1. System Prerequisites

Ensure the following tools are installed on the new machine:

| Component | Minimum Version | Download / Installation Command |
| :--- | :--- | :--- |
| **Git** | `git 2.30+` | `winget install Git.Git` (Windows) or `brew install git` (macOS) |
| **Python** | `Python 3.10+` (3.12 recommended) | `winget install Python.Python.3.12` or [python.org](https://www.python.org/) |
| **Node.js** | `Node.js 18+ LTS` (includes `npm` and `npx`) | `winget install OpenJS.NodeJS.LTS` or [nodejs.org](https://www.nodejs.org/) |

> [!IMPORTANT]
> If you just installed Node.js or Python, close and reopen your terminal/PowerShell so the updated `PATH` environment variables take effect. Verify with:
> ```bash
> node -v
> npm -v
> python --version
> ```

---

## 2. Clone the Repository

Clone the project to your desired directory:

```bash
git clone https://github.com/Nagaraju28/Playwright-Orchestrator.git
cd Playwright-Orchestrator
```

---

## 3. Terminal 1: Setup & Run Control Plane Server (Backend + UI)

The Control Plane manages the database, job queue, WebSocket telemetry broker, artifact storage, and the web dashboard.

### Step 3.1: Create and Activate Python Virtual Environment
**On Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```
*(If PowerShell restricts script execution, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

**On Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3.2: Install Server Dependencies
```bash
pip install --upgrade pip
pip install -r server/requirements.txt
```

### Step 3.3: Start the Control Plane Server
```bash
python -m uvicorn server.src.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 3.4: Verify Server Health
Open your web browser:
* **Interactive Dashboard:** [http://localhost:8000](http://localhost:8000)
* **API Documentation (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Health Endpoint:** [http://localhost:8000/health](http://localhost:8000/health)

*(Keep Terminal 1 running in the background).*

---

## 4. Terminal 2: Setup & Run Agent Daemon (Execution Worker)

The Agent Daemon is a lightweight background process that connects to the Control Plane via WebSocket, registers itself as an available worker, streams live test logs, and executes Playwright test suites.

### Step 4.1: Open a Second Terminal Window
Navigate to the `agent` directory:
```bash
cd Playwright-Orchestrator/agent
```

### Step 4.2: Install Node Dependencies
```bash
npm install
```

### Step 4.3: Install Playwright Chromium Browser
The agent needs Chromium to execute browser tests:
```bash
npx playwright install chromium
```
*(Optionally run `npx playwright install --with-deps` if on Linux to install required system packages).*

### Step 4.4: Start the Agent Daemon
```bash
npm start
```

### Step 4.5: Verify Agent Registration
In Terminal 2, you will see output like:
```text
========================================================
 Starting Playwright Orchestrator Agent Daemon
 Host: YOUR-PC | Platform: win32
========================================================
[Agent] Registering node 'agent-your-pc' with Control Plane at http://localhost:8000...
[Agent] Registered successfully! Agent ID: bcafb9e5-...
[AgentWS] Connecting to Control Plane at ws://localhost:8000/api/v1/ws/agent/...
[AgentWS] WebSocket connection established successfully.
```
Refresh **[http://localhost:8000](http://localhost:8000)** and click the **Agent Fleet** tab: your worker node will show as **`IDLE` (Healthy)** with a green badge!

---

## 5. Running Your First Test Run

1. Open **[http://localhost:8000](http://localhost:8000)**.
2. Under the **Projects** section, find **Swag Labs E-Commerce Regression** (auto-seeded).
3. Click the blue **"Trigger Run"** button.
4. **Watch Execution**:
   * **Chrome Browser Pop-Up**: Because `headless: false` and `slowMo: 600ms` are configured in `playwright.config.js`, Chrome will physically open on your screen and you will watch it log in and navigate the catalog!
   * **Live Terminal**: Click **"View Terminal & Details"** in the UI to watch stdout/stderr stream in real-time (<500ms latency) via Xterm.js.
   * **Milestone & Failure Screenshots**: Click on any test case in the test inspector to view the captured screenshots or click the thumbnail to open the modal view.

---

## 6. Distributed Setup (Agents on Separate Machines / VMs)

If your Agent Daemon runs on a different physical machine or VM than the Control Plane server:

1. In `agent/`: create a `.env` file or export environment variables:
   ```env
   CONTROL_PLANE_URL=http://<CONTROL_PLANE_IP>:8000
   CONTROL_PLANE_WS_URL=ws://<CONTROL_PLANE_IP>:8000/api/v1/ws
   AGENT_NAME=vm-worker-node-01
   ```
2. Start the daemon with `npm start`. The remote agent will connect securely over WebSocket.

---

## 7. Running Backend Automated Tests

To verify all API endpoints, ingestion, dispatcher, and watchdog invariants on the new system:

```powershell
# From the repository root with .venv active:
$env:PYTHONPATH = "."
pytest server/tests -v
```

All 13 integration and end-to-end acceptance tests should report **`PASSED`**.

---

## 8. Common Troubleshooting

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| **`npx : The term 'npx' is not recognized`** | Node.js not installed or terminal PATH not refreshed | Install Node.js LTS via `winget install OpenJS.NodeJS.LTS` and restart terminal. |
| **`No module named 'fastapi'`** | Python virtual environment not active | Activate `.venv` (`.venv\Scripts\Activate.ps1`) and run `pip install -r server/requirements.txt`. |
| **Job stays in `QUEUED` state** | Agent daemon is not running or disconnected | Open Terminal 2, navigate to `agent`, and execute `npm start`. The background dispatcher will immediately dispatch pending jobs. |
| **Browser doesn't open on desktop** | `headless: true` set in config | Set `headless: false` in `demo/ecommerce-playwright-suite/playwright.config.js`. |
| **Port 8000 in use** | Another process is using port 8000 | Kill process on 8000 or pass `--port 8080` to uvicorn and set `CONTROL_PLANE_URL=http://localhost:8080`. |
