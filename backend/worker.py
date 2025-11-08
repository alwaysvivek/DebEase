"""Async worker that pulls jobs and performs installs; publishes events to WSManager."""

import asyncio
import shlex
import time
from typing import Optional
from .repository import JobQueueRepository, InstallJob
from .ws_manager import WSManager
from .config import SIMULATE_INSTALL

class InstallerWorker:
    def __init__(self, queue_repo: JobQueueRepository, ws: WSManager, concurrency: int = 1):
        self.queue_repo = queue_repo
        self.ws = ws
        self.concurrency = concurrency
        self._tasks = []
        self._shutdown = asyncio.Event()

    async def start(self):
        for _ in range(self.concurrency):
            t = asyncio.create_task(self._run_loop())
            self._tasks.append(t)

    async def stop(self):
        self._shutdown.set()
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _run_loop(self):
        while not self._shutdown.is_set():
            job = await self.queue_repo.dequeue()
            if not job:
                await asyncio.sleep(0.1)
                continue
            await self._process_job(job)

    async def _process_job(self, job: InstallJob):
        job_id = job.job_id
        await self.queue_repo.update_job_status(job_id, status="running", started_at=time.time())
        await self.ws.broadcast({"type": "job_started", "job_id": job_id, "package": job.package, "timestamp": time.time()})
        if SIMULATE_INSTALL:
            # Simulate: emit lines and progress
            for i in range(5):
                line = f"Simulated output for {job.package} step {i+1}"
                await asyncio.sleep(0.25)
                # Append to log (naive: fetch job from repo then update)
                # For brevity we won't re-fetch the object; update via update_job_status to replace log
                current_job = await self.queue_repo.get_job(job_id)
                new_log = (current_job.log if current_job else []) + [line]
                await self.queue_repo.update_job_status(job_id, log=new_log)
                await self.ws.broadcast({"type": "stdout", "job_id": job_id, "line": line, "timestamp": time.time()})
                await self.ws.broadcast({"type": "progress", "job_id": job_id, "percent": int((i+1)/5*100), "timestamp": time.time()})
            await self.queue_repo.update_job_status(job_id, status="finished", finished_at=time.time(), exit_code=0)
            await self.ws.broadcast({"type": "job_finished", "job_id": job_id, "success": True, "exit_code": 0, "timestamp": time.time()})
            return

        # If not simulating, run apt install (requires sudo/root)
        cmd = f"sudo apt-get install -y {shlex.quote(job.package)}"
        process = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        try:
            assert process.stdout is not None
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                decoded = line.decode(errors="ignore").rstrip("\n")
                current_job = await self.queue_repo.get_job(job_id)
                new_log = (current_job.log if current_job else []) + [decoded]
                await self.queue_repo.update_job_status(job_id, log=new_log)
                await self.ws.broadcast({"type": "stdout", "job_id": job_id, "line": decoded, "timestamp": time.time()})
            rc = await process.wait()
            success = (rc == 0)
            await self.queue_repo.update_job_status(job_id, status="finished" if success else "failed", finished_at=time.time(), exit_code=rc)
            await self.ws.broadcast({"type": "job_finished", "job_id": job_id, "success": success, "exit_code": rc, "timestamp": time.time()})
        except asyncio.CancelledError:
            process.kill()
            await process.wait()
            await self.queue_repo.update_job_status(job_id, status="failed", finished_at=time.time(), exit_code=-1)
            await self.ws.broadcast({"type": "job_finished", "job_id": job_id, "success": False, "exit_code": -1, "timestamp": time.time()})