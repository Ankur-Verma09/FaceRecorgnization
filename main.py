import os
import sys
import time
import threading
import uvicorn
import webview
from pathlib import Path

# Ensure backend package import path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from backend.app import app

def run_fastapi():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")

if __name__ == "__main__":
    print("Starting Offline AI Face Recognition & Photo Organizer Desktop App...")

    # Start FastAPI backend server in a background daemon thread
    server_thread = threading.Thread(target=run_fastapi, daemon=True)
    server_thread.start()

    # Wait 1.5 seconds for FastAPI server to initialize
    time.sleep(1.5)

    # Launch PyWebView desktop application window
    window = webview.create_window(
        title="Offline AI Face Recognition & Photo Organizer",
        url="http://127.0.0.1:8000",
        width=1280,
        height=850,
        min_size=(1024, 700),
        resizable=True
    )
    webview.start()
