#!/usr/bin/env python3
"""
CLISApp Backend Development Server (DEPRECATED)

⚠️  DEPRECATED: This script is deprecated in Phase 1 and will be removed in Phase 2.

Migration Path: Use the root Makefile instead
  - For API service:   make api-up  (from repo root)
  - For all services:  make up      (from repo root)

This script remains functional for backward compatibility but is no longer
the recommended entry point.
"""

import uvicorn
import sys
from pathlib import Path

# Add the app directory to Python path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

from app.core.config import settings

if __name__ == "__main__":
    # Display deprecation warning
    print("=" * 70)
    print("⚠️  DEPRECATION WARNING")
    print("=" * 70)
    print("\nThis script (dev_server.py) is DEPRECATED and will be removed in Phase 2.")
    print("\n📌 Recommended: Use 'make api-up' from the repo root instead")
    print("\nContinuing for backward compatibility...\n")
    print("=" * 70)
    print()

    print(f"🚀 Starting {settings.app_name} v{settings.app_version}")
    print(f"📍 Server: http://{settings.host}:{settings.port}")
    print(f"📚 API Docs: http://{settings.host}:{settings.port}/docs")
    print(f"🗂️  Data Directory: {settings.data_root}")
    print("=" * 50)
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,  # Enable hot reload for development
        log_level=settings.log_level.lower(),
        access_log=True
    )
