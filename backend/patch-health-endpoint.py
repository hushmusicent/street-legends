#!/usr/bin/env python3
"""Add a GET /health endpoint to the backend.

The server log is full of `GET /health 404 Not Found` — Emergent's health
checker (and anything else probing the service) hits /health, but the app
never defined it (the only root route is /api/ under the api router). A
404 on the health check makes the platform think the backend is down.

Change (backend/server.py, right after the FastAPI app is created):
  @app.get("/health") -> {"status": "ok"}

This is a BACKEND patch: run in /app, then Deploy (Publish).
Marker: HEALTH_ENDPOINT_OK
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

ANCHOR = '# Create a router with the /api prefix\napi_router = APIRouter(prefix="/api")'

NEW = '''# Health check (Emergent / load balancer probes GET /health)
@app.get("/health")
async def health():
    return {"status": "ok"}

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")'''


def main():
    if not SERVER.exists():
        print("HEALTH_ENDPOINT_FAIL backend/server.py not found")
        return 1
    src = SERVER.read_text(encoding="utf-8")
    if '@app.get("/health")' in src:
        print("HEALTH_ENDPOINT_ALREADY_APPLIED")
        return 0
    if ANCHOR not in src:
        print("HEALTH_ENDPOINT_FAIL anchor not found (file may have changed)")
        return 1
    src = src.replace(ANCHOR, NEW, 1)
    if '@app.get("/health")' not in src:
        print("HEALTH_ENDPOINT_FAIL insert did not land")
        return 1
    SERVER.write_text(src, encoding="utf-8")
    print("HEALTH_ENDPOINT_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
