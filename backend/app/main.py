"""
Peq Backend Server
FastAPI application serving the automation engine, API, and dashboard.
"""
import os
import sys

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from datetime import datetime

from .api.routes import router as api_router
from .core.config import settings


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered automation engine. Describe what you want in plain English, it builds and runs it.",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root_page():
    """Serve the dashboard."""
    static_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")
    index_path = os.path.join(static_path, "dashboard.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"app": settings.APP_NAME, "version": settings.APP_VERSION, "status": "running"}

@app.get("/landing")
async def landing_page():
    """Serve the marketing landing page."""
    landing_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "landing", "index.html")
    if os.path.exists(landing_path):
        return FileResponse(landing_path)
    return {"error": "Landing page not found", "path": landing_path}


# Mount static files
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", settings.RUNNER_PORT))
    uvicorn.run(app, host="0.0.0.0", port=port)
