# Business Requirements Document (BRD)
## Enterprise Playwright Test Orchestrator (UiPath Test Suite Style)

**Document Version:** 1.0  
**Status:** Draft / Proposed  
**Target Audience:** Engineering Leadership, DevOps, Frontend/Backend Developers, QA Automation Teams  

---

## 1. Executive Summary
Modern QA engineering teams require enterprise-grade governance, remote execution management, real-time log monitoring, and centralized metrics for their Playwright automation suites. Currently, running scripts across distributed Virtual Machines (VMs) often requires custom shell scripts, fragmented CI/CD pipelines, and lack centralized visibility. 

The **Playwright Test Orchestrator** aims to bridge this gap by functioning as an internal "UiPath Test Suite" style platform. It empowers teams to upload test bundles or connect Git repositories, trigger executions across registered worker VMs, monitor live terminal streams, and track aggregate pass/fail metrics through a unified web dashboard.

---

## 2. Project Scope & Objectives

### In-Scope
* **Centralized Dashboard UI:** Project management, execution triggers, live log streaming terminal, and historical analytics.
* **Control Plane API & Database:** User management, project settings, job queues, and test result storage.
* **Agent Daemon (Execution Plane):** Lightweight cross-platform service running on target VMs for automated setup, execution, and telemetry reporting.
* **Source Control Integration:** Support for Git repositories (branch selection, cloning/pulling) and direct zip archive uploads.
* **Test Reporting & Artifacts:** Automated extraction of Playwright JSON/JUnit reports, metrics aggregation, and trace/screenshot/video storage.

### Out-of-Scope (for MVP)
* Automated elastic provisioning of cloud VMs (assuming VMs are pre-provisioned and register themselves).
* Advanced role-based access control (RBAC) granular permission matrices beyond standard team separation.

---

## 3. Stakeholders & Personas

| Persona | Role / Description | Core Needs |
| :--- | :--- | :--- |
| **QA Automation Engineer** | Writes and maintains Playwright test suites. | Easy script upload/Git linking, rapid execution feedback, deep debugging traces. |
| **QA / Engineering Manager** | Oversees test coverage and quality gates. | High-level pass/fail dashboards, trend analytics, execution history metrics. |
| **DevOps / Infrastructure Engineer** | Manages worker VMs and agent stability. | Low-overhead agent daemon, secure token authentication, resource health monitoring. |

---

## 4. Functional Requirements

### 4.1 Project & Source Management
* **FR-1.1:** Users must be able to create distinct projects within the platform.
* **FR-1.2:** Projects must support two ingestion methods:
  1. *Git Integration:* Providing a repository URL and branch name.
  2. *Direct Upload:* Uploading a zipped archive of the Playwright workspace.
* **FR-1.3:** The system must securely store repository credentials or personal access tokens (PATs) if authentication is required for private Git repositories.

### 4.2 Job Execution & Orchestration
* **FR-2.1:** Users must be able to trigger a manual test run specifying target parameters (environment, tags, worker VM pool).
* **FR-2.2:** The Control Plane must queue incoming execution requests and dispatch them to an available, healthy Agent VM.
* **FR-2.3:** The Agent Daemon must automatically prepare the workspace (git clone/pull or zip extraction) and execute dependency installation (`npm ci`).
* **FR-2.4:** The Agent must run Playwright tests using custom CLI arguments and reporting flags.

### 4.3 Real-Time Monitoring (Live Logs)
* **FR-3.1:** The Agent must capture standard output (`stdout`) and standard error (`stderr`) during test execution.
* **FR-3.2:** The system must stream logs in real-time from the Agent VM to the Control Plane via WebSockets.
* **FR-3.3:** The frontend dashboard must render live logs inside an interactive terminal interface (e.g., Xterm.js).

### 4.4 Metrics, Reporting, & Artifacts
* **FR-4.1:** The system must parse Playwright JSON/JUnit result outputs upon job completion.
* **FR-4.2:** The dashboard must display aggregate metrics including total test cases, passed count, failed count, skipped count, and total execution duration.
* **FR-4.3:** The Agent must upload failure artifacts (screenshots, videos, trace files) to object storage (MinIO/S3) linked to the specific test case record.

---

## 5. Non-Functional Requirements

* **NFR-1 (Performance):** WebSocket log streaming latency between the execution agent and the UI dashboard should not exceed $500\text{ ms}$ under normal network conditions.
* **NFR-2 (Scalability):** The Control Plane architecture must support horizontal scaling to handle multiple concurrent job queues and agent connections.
* **NFR-3 (Security):** Communication between VM agents and the Control Plane must use secure tokens and encrypted WebSocket/HTTPS protocols.
* **NFR-4 (Reliability):** If an Agent VM disconnects mid-execution, the Control Plane must mark the job as `failed`/`orphaned` and alert the user gracefully.

---

## 6. Proposed System Architecture & Tech Stack

* **Frontend:** React, Tailwind CSS, Xterm.js (for live terminal logs).
* **Control Plane API:** Python (FastAPI) with async WebSocket management.
* **Database:** PostgreSQL (Projects, Jobs, Test Results, Agents metadata).
* **Agent Daemon:** Node.js service running on target VMs.
* **Artifact Storage:** S3-compatible object storage (MinIO / AWS S3).

---

## 7. Acceptance Criteria & Success Metrics

* **AC-1:** A user can input a Git URL and branch, trigger a run, and see the execution status change from `queued` to `running` to `passed/failed`.
* **AC-2:** Live logs stream successfully into the browser terminal view while tests are actively running on a remote VM.
* **AC-3:** Post-execution, the dashboard accurately reflects aggregate test counts matching the Playwright execution report summary.