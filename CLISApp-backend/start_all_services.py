#!/usr/bin/env python3
"""
CLISApp Backend - Unified Service Launcher
Starts both Main API Service and Tile Server simultaneously
"""

import uvicorn
import sys
import signal
from pathlib import Path
from multiprocessing import Process
import logging

# Add project path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global process list
processes = []

def start_main_api():
    """Start Main API Service (port 8080)"""
    logger.info("🚀 Starting Main API Service...")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,  # 8080
        reload=False,  # Disable reload in multiprocessing to avoid daemon issues
        log_level=settings.log_level.lower(),
        access_log=True
    )

def start_tile_server():
    """Start Tile Server (port 8000)"""
    logger.info("🗺️  Starting Tile Server...")
    
    # Add data_pipeline/servers directory to path
    tile_server_dir = app_dir / "data_pipeline" / "servers"
    sys.path.insert(0, str(tile_server_dir))
    
    uvicorn.run(
        "tile_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload in multiprocessing to avoid daemon issues
        log_level="info",
        access_log=True
    )

def signal_handler(sig, frame):
    """Handle Ctrl+C signal"""
    logger.info("\n\n👋 Shutdown signal received, stopping all services...")
    
    # Terminate all child processes
    for process in processes:
        if process.is_alive():
            logger.info(f"Terminating process: {process.name}")
            process.terminate()
            process.join(timeout=5)
            if process.is_alive():
                logger.warning(f"Force killing process: {process.name}")
                process.kill()
    
    logger.info("✅ All services stopped")
    sys.exit(0)

def main():
    """Main entry point"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("=" * 70)
    print(f"🌏 {settings.app_name} v{settings.app_version}")
    print("=" * 70)
    print("\nStarting all backend services...\n")
    
    # Create and start Main API Service process
    api_process = Process(
        target=start_main_api,
        name="MainAPI-Service"
    )
    # Don't set daemon=True to allow uvicorn to spawn child processes if needed
    api_process.start()
    processes.append(api_process)
    
    # Give the first service some time to start
    import time
    time.sleep(2)
    
    # Create and start Tile Server process
    tile_process = Process(
        target=start_tile_server,
        name="TileServer-Service"
    )
    # Don't set daemon=True to allow uvicorn to spawn child processes if needed
    tile_process.start()
    processes.append(tile_process)
    
    # Wait for services to start
    time.sleep(2)
    
    # Display service information
    print("\n" + "=" * 70)
    print("✅ All services started successfully!")
    print("=" * 70)
    print("\n📡 Service URLs:")
    print(f"   • Main API Service:        http://{settings.host}:{settings.port}")
    print(f"   • API Documentation:       http://{settings.host}:{settings.port}/docs")
    print(f"   • Tile Server:             http://0.0.0.0:8000")
    print(f"   • Tile Server Docs:        http://localhost:8000/docs")
    print(f"   • Tile Demo Page:          http://localhost:8000/tiles/pm25/demo")
    print("\n🗂️  Data Directory:")
    print(f"   • {settings.data_root}")
    print("\n💡 Tips:")
    print("   • iOS Simulator:      http://localhost:8080 and http://localhost:8000")
    print("   • Android Emulator:   http://10.0.2.2:8080 and http://10.0.2.2:8000")
    print("   • Physical Device:    http://192.168.0.97:8080 and http://192.168.0.97:8000")
    print("\n🛑 Press Ctrl+C to stop all services")
    print("=" * 70)
    print()
    
    # Keep main process running and monitor child processes
    try:
        while True:
            # Check if all processes are still running
            all_alive = all(p.is_alive() for p in processes)
            
            if not all_alive:
                logger.error("❌ Service crash detected, restarting...")
                for process in processes:
                    if not process.is_alive():
                        logger.warning(f"Process {process.name} exited, restarting...")
                        process.start()
            
            time.sleep(1)
    
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()

