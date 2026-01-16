#!/usr/bin/env python3
"""Start both main.py (worker) and web server."""

import subprocess
import sys
import os
import time
import signal

def main():
    # Start worker (main.py) in background
    print("🚀 Starting Matrix Watcher worker...")
    worker = subprocess.Popen([sys.executable, "main.py"])
    
    # Give worker time to initialize
    time.sleep(3)
    
    # Start web server (blocks)
    print("🌐 Starting web server...")
    web = subprocess.Popen([sys.executable, "web/server.py"])
    
    def shutdown(signum, frame):
        print("\n🛑 Shutting down...")
        worker.terminate()
        web.terminate()
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    
    # Wait for processes
    try:
        web.wait()
    except KeyboardInterrupt:
        shutdown(None, None)

if __name__ == "__main__":
    main()
