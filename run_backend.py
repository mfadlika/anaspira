from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn


PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


if __name__ == "__main__":
    # Read port from environment (Render/Back4App) or default to 3000 for local dev
    port = int(os.environ.get("PORT", "3000"))
    # In production (where PORT is set), bind to 0.0.0.0 and disable reload for performance
    host = "0.0.0.0" if "PORT" in os.environ else "127.0.0.1"
    reload = False if "PORT" in os.environ else True
    
    print(f"Starting Backend on {host}:{port}...")
    uvicorn.run("backend.main:app", host=host, port=port, reload=reload)