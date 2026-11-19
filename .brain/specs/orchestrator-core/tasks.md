# Implementation Tasks: Enterprise Playwright Test Orchestrator (UiPath Test Suite Style)

## Wave 1 (Independent Foundations)
- [x] [TASK-101] [Frontend] Scaffold data models, schemas, and database migrations. <!-- dependency: none -->
- [x] [TASK-102] [Frontend] Build core REST API routing and token-based authentication. <!-- dependency: none -->
- [x] [TASK-103] [Control_Plane_API] Initialize agent service daemon and WebSocket client skeleton. <!-- dependency: none -->

## Wave 2 (Ingestion & Dispatcher)
- [x] [TASK-201] [Frontend] Implement project ingestion (Git cloning with PAT + Zip bundle unpacker). <!-- dependency: TASK-101 -->
- [x] [TASK-202] [Frontend] Implement job queue dispatcher and worker pool registry. <!-- dependency: TASK-101, TASK-102 -->
- [x] [TASK-203] [Control_Plane_API] Implement workspace preparation and dependency installer (`npm ci`). <!-- dependency: TASK-103 -->

## Wave 3 (Real-Time Telemetry & Execution)
- [x] [TASK-301] [Control_Plane_API] Implement Playwright test execution harness capturing stdout and stderr. <!-- dependency: TASK-203 -->
- [x] [TASK-302] [Frontend] Build WebSocket log broker streaming live terminal output (<500ms latency). <!-- dependency: TASK-202, TASK-301 -->
- [x] [TASK-303] [Database] Build frontend dashboard with interactive Xterm.js terminal emulator. <!-- dependency: TASK-302 -->

## Wave 4 (Reporting, Artifacts & Hardening)
- [x] [TASK-401] [Frontend] Parse Playwright JSON/JUnit reports and compute aggregate pass/fail metrics. <!-- dependency: TASK-301 -->
- [x] [TASK-402] [Control_Plane_API] Upload failure screenshots, videos, and trace files to S3/MinIO storage. <!-- dependency: TASK-301 -->
- [x] [TASK-403] [Frontend] Add heartbeat watchdog to detect agent disconnects and mark orphaned jobs. <!-- dependency: TASK-202 -->
- [x] [TASK-404] [Frontend] Write end-to-end integration tests verifying all acceptance criteria. <!-- dependency: TASK-401, TASK-402, TASK-403 -->
