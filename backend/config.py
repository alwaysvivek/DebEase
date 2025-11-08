# Small config module for DebEase realtime installer

import os

PORT = int(os.environ.get("DEBEASE_PORT", "8080"))
HOST = os.environ.get("DEBEASE_HOST", "0.0.0.0")
SIMULATE_INSTALL = os.environ.get("DEBEASE_SIMULATE_INSTALL", "true").lower() in ("1", "true", "yes")
WORKER_CONCURRENCY = int(os.environ.get("DEBEASE_WORKER_CONCURRENCY", "1"))
