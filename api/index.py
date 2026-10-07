"""Vercel Serverless Function entry point for Smart Support Dispatcher & Ticketing System."""

import sys
from pathlib import Path

from fastapi import Request

api_dir = Path(__file__).resolve().parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from support_dispatcher.api.app import create_app  # noqa: E402

app = create_app()


@app.middleware("http")
async def normalize_vercel_path(request: Request, call_next):
    """Normalizes path rewritten by Vercel from /api/index.py/$1 to the original path."""
    path = request.scope.get("path", "")
    for prefix in ["/api/index.py", "/api/index"]:
        if path.startswith(prefix):
            new_path = path[len(prefix) :] or "/"
            request.scope["path"] = new_path
            break
    return await call_next(request)


@app.get("/")
def root_status() -> dict[str, str]:
    """Root status endpoint for Vercel deployment."""
    return {"status": "healthy", "service": "Smart Support Dispatcher & Ticketing System"}
