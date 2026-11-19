# Technical Design: Enterprise Playwright Test Orchestrator (UiPath Test Suite Style)

## Architecture & Components
- **Frontend**: Built using React, Tailwind CSS, Xterm.js (for live terminal logs).. Handles orchestration, boundaries, and persistence.
- **Control Plane API**: Built using Python (FastAPI) with async WebSocket management.. Handles orchestration, boundaries, and persistence.
- **Database**: Built using PostgreSQL (Projects, Jobs, Test Results, Agents metadata).. Handles orchestration, boundaries, and persistence.
- **Agent Daemon**: Built using Node.js service running on target VMs.. Handles orchestration, boundaries, and persistence.
- **Artifact Storage**: Built using S3-compatible object storage (MinIO / AWS S3).. Handles orchestration, boundaries, and persistence.

## Data Flow & Sequence
1. **Trigger & Validation**: Client or developer triggers execution with project and environment parameters.
2. **Dispatch & Workspace Setup**: The Control Plane queues the job, routes to an available agent, and prepares the workspace.
3. **Execution & Real-time Telemetry**: Tests execute while live stdout/stderr streams back to the dashboard over WebSockets.
4. **Reporting & Artifact Archival**: Test summaries (JSON/JUnit) are indexed in the database and failure artifacts uploaded to object storage.

## Error Handling & Invariants
- **[INVARIANT]**: NFR-1 (Performance): WebSocket log streaming latency between the execution agent and the UI dashboard should not exceed $500\text{ ms}$ under normal network conditions.
- **[INVARIANT]**: NFR-2 (Scalability): The Control Plane architecture must support horizontal scaling to handle multiple concurrent job queues and agent connections.
- **[INVARIANT]**: NFR-3 (Security): Communication between VM agents and the Control Plane must use secure tokens and encrypted WebSocket/HTTPS protocols.
- **[INVARIANT]**: NFR-4 (Reliability): If an Agent VM disconnects mid-execution, the Control Plane must mark the job as `failed`/`orphaned` and alert the user gracefully.
- **Boundaries**: State mutations must be transactional; invalid payloads fail early with 400 Bad Request.
- **Resilience**: Agent disconnections mid-flight must be captured by heartbeats and marked as failed/orphaned.
