#!/usr/bin/env python3
"""
VibeCortex Application Launcher
Run this script to start the FastAPI web application
"""

import uvicorn
import sys
import os
from pathlib import Path

# Get the project root directory
project_root = Path(__file__).parent
backend_dir = project_root / "backend"

# Change to the backend directory
os.chdir(backend_dir)

# Add the backend directory to Python path
sys.path.insert(0, str(backend_dir))

if __name__ == "__main__":
    print("🚀 Starting VibeCortex Data Labeling Tool...")
    print("📍 Backend: FastAPI with SQLAlchemy database")
    print("🎨 Frontend: Modern responsive UI with image annotation")
    print("🌐 Server: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/api/docs")
    print("=" * 50)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        reload_dirs=[
            str(backend_dir),
            str(project_root / "templates"),
            str(project_root / "static"),
        ],
    )
