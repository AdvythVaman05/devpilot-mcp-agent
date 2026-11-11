"""
DevPilot FastAPI Application Setup
"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from devpilot.api.routes import router
from devpilot.config import settings

app = FastAPI(
    title="DevPilot - MCP Software Engineering Agent API",
    description="Autonomous software engineering agent powered by Model Context Protocol (MCP) and Google Gemini.",
    version=settings.APP_VERSION,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:5173",
        "https://devpilot-mcp-agent.vercel.app",
        "https://frontend-lake-gamma-28.vercel.app",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(router)


@app.get("/")
def get_root():
    """Root endpoint providing service metadata."""
    return {
        "service": "DevPilot Backend API",
        "status": "online",
        "protocol": "Model Context Protocol (MCP) 2.x",
        "health": "/api/health",
        "docs": "/docs",
        "frontend": "https://devpilot-mcp-agent.vercel.app",
    }


# Serve built frontend static files if present
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists() and frontend_dist.is_dir():
    app.mount("/app", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

