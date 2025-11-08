"""FastAPI app exposing HTTP endpoints and WebSocket for DebEase real-time installs."""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import asyncio
from .repository import PackageRepository, JobQueueRepository
from .ws_manager import WSManager
from .worker import InstallerWorker
from .config import PORT, HOST, WORKER_CONCURRENCY
import uvicorn
import os

app = FastAPI(title="DebEase Orchestrator")

# repositories and manager (singletons for process)
package_repo = PackageRepository()
job_repo = JobQueueRepository()
ws_manager = WSManager()
worker = InstallerWorker(job_repo, ws_manager, concurrency=WORKER_CONCURRENCY)

# Mount static UI
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.on_event("startup")
async def startup_event():
    await worker.start()

@app.on_event("shutdown")
async def shutdown_event():
    await worker.stop()

@app.get("/packages")
async def list_packages(q: str = None, page: int = 1, size: int = 30):
    return await package_repo.search(q=q, page=page, size=size)

@app.post("/enqueue")
async def enqueue_install(payload: dict):
    package = payload.get("package")
    if not package:
        raise HTTPException(status_code=400, detail="package required")
    job = await job_repo.enqueue(package)
    return {"job_id": job.job_id, "status": job.status}

@app.get("/queue")
async def get_queue():
    return await job_repo.list_jobs()

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            # Keep the connection alive; optionally accept client control messages in future.
            msg = await ws.receive_text()  # not used now
            # Optionally: parse subscribe messages
    except WebSocketDisconnect:
        await ws_manager.disconnect(ws)

# simple index for convenience
@app.get("/", response_class=HTMLResponse)
async def index():
    index_path = os.path.join(static_dir, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

def main():
    uvicorn.run("backend.app:app", host=HOST, port=PORT, reload=False)

if __name__ == "__main__":
    main()
