# DebEase

DebEase is a post-install orchestration tool for Debian-based systems with a lightweight web UI.  
This repository adds a realtime installer service that accepts install requests, runs package installations (or simulates them for development), and streams logs and progress to web clients via WebSockets.

This README describes the current implementation (backend and frontend), how to run it, the API and WebSocket message formats, configuration, and development notes.

---

## Highlights / Goals

- Real-time installation orchestration with WebSocket streaming of logs and progress.
- Simple searchable package catalog and enqueueable install queue.
- Safe development mode (SIMULATE_INSTALL) so you can test without root or changing the system.
- Minimal, modular server written with FastAPI + asyncio:
  - backend/repository.py — Repository pattern for package metadata and an in-memory job queue.
  - backend/worker.py — Async InstallerWorker that processes jobs and broadcasts events.
  - backend/ws_manager.py — WebSocket manager to broadcast messages to connected clients.
  - backend/app.py — FastAPI app exposing HTTP endpoints and a WebSocket endpoint.
  - backend/config.py — Small config module for environment-driven configuration.
- Static frontend under `static/` that consumes REST endpoints and the WebSocket stream.

---

## Architecture (high level)

Client browser ⇄ FastAPI HTTP endpoints (enqueue, packages, queue)  
Client browser ⇄ WebSocket (ws://server/ws) ⇄ WSManager ⇄ InstallerWorker ⇄ apt / simulated commands

Key design choices:
- Repository pattern isolates data operations (easy to replace with DB later).
- Async worker + asyncio subprocess provides non-blocking operations and concurrent handling.
- WebSocket manager provides a lightweight broadcast channel for realtime UI updates.

---

## What’s implemented

- HTTP endpoints:
  - GET /packages — search and pagination for the package catalog.
  - POST /enqueue — enqueue a package install job.
  - GET /queue — list current jobs and status.
  - GET / — serves the static web UI from `static/index.html`.
- WebSocket:
  - /ws — broadcast realtime events: job_started, stdout, progress, job_finished.
- InstallerWorker:
  - SIMULATE_INSTALL mode (default) emits simulated logs/progress for safe development.
  - Real install mode executes `sudo apt-get install -y <package>` (requires root/sudo).
- In-memory job repository and queue. (Replaceable with persistent storage later.)
- Minimal static UI: `static/index.html`, `static/app.js`, `static/styles.css`.

---

## Quickstart (development / local)

Requirements:
- Python 3.9+
- Recommended packages: fastapi, uvicorn

Install dependencies:
```bash
pip install fastapi uvicorn
```

Run the server (simulate mode — safe for local use):
```bash
export DEBEASE_SIMULATE_INSTALL=true
python -m backend.app
# by default listens on 0.0.0.0:8080 (configurable)
```

Open a browser: http://localhost:8080/ — the UI lists packages, allows enqueueing installs, and shows realtime logs.

To run real installs (not recommended on development machines):
- Set `DEBEASE_SIMULATE_INSTALL=false` and run the process as a user with appropriate privileges (apt install requires root/sudo).

---

## Configuration (environment variables)

- DEBEASE_PORT — port to listen on (default: `8080`).
- DEBEASE_HOST — host to bind (default: `0.0.0.0`).
- DEBEASE_SIMULATE_INSTALL — `"true"` (default) to simulate installs; set to `"false"` to run `apt-get`.
- DEBEASE_WORKER_CONCURRENCY — number of concurrent worker tasks (default: `1`).

---

## API Reference

List packages:
```
GET /packages?q=<query>&page=<n>&size=<s>
Response: { total, page, size, items: [ { name, description, version, tags } ] }
```

Enqueue a package:
```
POST /enqueue
Body (JSON): { "package": "vim" }
Response: { "job_id": "<uuid>", "status": "queued" }
```

List jobs:
```
GET /queue
Response: [ { job_id, package, status, created_at, started_at?, finished_at?, exit_code?, log? } ]
```

WebSocket endpoint:
```
ws://<host>:<port>/ws
```

WebSocket message examples (JSON):
- job_started
  ```json
  {"type":"job_started","job_id":"...","package":"nginx","timestamp":1234567890.1}
  ```
- stdout
  ```json
  {"type":"stdout","job_id":"...","line":"some output","timestamp":1234567890.2}
  ```
- progress
  ```json
  {"type":"progress","job_id":"...","percent":40,"timestamp":1234567890.3}
  ```
- job_finished
  ```json
  {"type":"job_finished","job_id":"...","success":true,"exit_code":0,"timestamp":1234567890.4}
  ```

Clients may connect and listen to all events and filter locally by `job_id`. The current implementation broadcasts to all clients (simple pub/sub).

---

## Testing

A small set of unit tests is included under `tests/` (repository and ws manager). Tests are async-friendly using pytest. Example:

```bash
pip install pytest
pytest
```

Note: Integration / E2E tests that exercise the full flow require the server to be running (or can be adapted to use TestClient/AsyncClient to run the app in-process).

---

## Development notes

- Files of interest:
  - backend/repository.py — PackageRepository, JobQueueRepository
  - backend/worker.py — InstallerWorker implementation
  - backend/ws_manager.py — WSManager broadcasting logic
  - backend/app.py — FastAPI application / endpoints and startup/shutdown lifecycle
  - static/* — frontend assets
- The in-memory repositories make it easy to iterate quickly. For production, consider:
  - Persisting jobs in a database (SQLite/Postgres).
  - Using a message broker (Redis/RabbitMQ) for multi-process or multi-host worker coordination.
  - Adding authentication/authorization to API endpoints.

---

## Contribution

Contributions are welcome. Suggested next improvements:
- Convert JobQueueRepository to a Redis-backed queue for durability and scaling.
- Replace in-memory package catalog with a persisted catalog and package metadata syncing.
- Add authentication and role-based authorization for enqueueing packages.
- Improve frontend UX: job details, per-job filtering, and log search.

When opening PRs:
- Target branch: `main` (or open from `feature/*` branches).
- Include tests for added functionality and documentation updates when appropriate.

---
