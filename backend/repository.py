"""Repository pattern for package metadata and job queue."""

from typing import List, Dict, Optional
import uuid
import asyncio
from dataclasses import dataclass, field
import time

dataclass
class PackageMetadata:
    name: str
    description: str = ""
    version: str = ""
    tags: List[str] = field(default_factory=list)

dataclass
class InstallJob:
    job_id: str
    package: str
    status: str  # queued, running, finished, failed
    created_at: float
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    exit_code: Optional[int] = None
    log: List[str] = field(default_factory=list)

class PackageRepository:
    """In-memory repository for package metadata. Replaceable with DB later."""
    def __init__(self):
        self._packages: Dict[str, PackageMetadata] = {}
        self._lock = asyncio.Lock()
        # preload some sample packages
        for name in ["vim", "git", "curl", "htop", "nginx"]:
            self._packages[name] = PackageMetadata(name=name, description=f"{name} package", version="latest")

    async def search(self, q: Optional[str] = None, page: int = 1, size: int = 30):
        async with self._lock:
            items = list(self._packages.values())
            if q:
                ql = q.lower()
                items = [p for p in items if ql in p.name.lower() or ql in p.description.lower() or ql in " ".join(p.tags)]
            start = (page - 1) * size
            end = start + size
            total = len(items)
            return {"total": total, "page": page, "size": size, "items": [p.__dict__ for p in items[start:end]]}

class JobQueueRepository:
    """Simple in-memory job queue for install jobs."""
    def __init__(self):
        self._jobs: Dict[str, InstallJob] = {}
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._lock = asyncio.Lock()

    async def enqueue(self, package: str) -> InstallJob:
        job_id = str(uuid.uuid4())
        job = InstallJob(job_id=job_id, package=package, status="queued", created_at=time.time())
        async with self._lock:
            self._jobs[job_id] = job
        await self._queue.put(job_id)
        return job

    async def dequeue(self) -> Optional[InstallJob]:
        job_id = await self._queue.get()
        async with self._lock:
            job = self._jobs.get(job_id)
            return job

    async def get_job(self, job_id: str) -> Optional[InstallJob]:
        async with self._lock:
            return self._jobs.get(job_id)

    async def list_jobs(self):
        async with self._lock:
            return [j.__dict__ for j in self._jobs.values()]

    async def update_job_status(self, job_id: str, **fields):
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            for k, v in fields.items():
                setattr(job, k, v)
