# DebEase - Real-time Installer (Enhancement)

## New features
1. Real-time installation orchestration (WebSocket streaming of install logs and progress).
2. Searchable package catalog + enqueue install queue.

## Running locally (development, simulate mode)
1. Ensure Python 3.9+ installed.
2. Install dependencies:
   pip install fastapi uvicorn pytest httpx websocket-client
3. Start server (simulate mode by default):
   export DEBEASE_SIMULATE_INSTALL=true
   python -m backend.app
4. Open browser at http://localhost:8080/ to view UI. Click Install to enqueue simulated installs.

## Production notes
- To perform real installs set DEBEASE_SIMULATE_INSTALL=false and run as a user with sudo privileges. Installing packages requires root.
- Configure WORKER_CONCURRENCY environment variable to increase concurrent installs (default 1).

## End-to-end test
- Start the server (as above).
- Run pytest to execute unit tests. Integration tests may require the app to be listening.

## Environment variables
- DEBEASE_SIMULATE_INSTALL (default true) — if true, worker simulates installs.
- DEBEASE_PORT (default 8080)
- DEBEASE_HOST (default 0.0.0.0)
- DEBEASE_WORKER_CONCURRENCY (default 1)

## Design notes
- Repository pattern used in backend/repository.py to isolate data-access logic.
- Async worker + WebSocket manager used to provide real-time updates to clients.
