"""
DevPilot Entrypoint
Launches the FastAPI server with MCP agent orchestrator and frontend support.
"""
import argparse
import os
import uvicorn
from devpilot.config import settings


def main():
    parser = argparse.ArgumentParser(description="DevPilot MCP Software Engineering Agent Server")
    default_port = int(os.environ.get("PORT", settings.PORT))
    default_host = os.environ.get("HOST", settings.HOST)
    parser.add_argument("--host", default=default_host, help="Host address to bind")
    parser.add_argument("--port", type=int, default=default_port, help="Port to bind")
    parser.add_argument("--reload", action="store_true", help="Enable live code reloading")
    args = parser.parse_args()

    print(f"[DevPilot] Starting server on http://{args.host}:{args.port}")
    uvicorn.run("devpilot.api.app:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
