import sys
import time
import subprocess
import urllib.request
import json
from pathlib import Path

SERVER_DIR = Path(__file__).parent
SERVER_SCRIPT = SERVER_DIR / "server.py"
LOG_FILE = SERVER_DIR / "server.log"

def is_server_running() -> bool:
    try:
        req = urllib.request.Request("http://127.0.0.1:7357/api/health", headers={"User-Agent": "HealthCheck"})
        with urllib.request.urlopen(req, timeout=0.8) as resp:
            return resp.status == 200
    except Exception:
        return False

def start_server():
    if is_server_running():
        print(json.dumps({"status": "already_running", "url": "http://127.0.0.1:7357"}))
        return

    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS

    log_fp = open(LOG_FILE, "a", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, str(SERVER_SCRIPT)],
        stdin=subprocess.DEVNULL,
        stdout=log_fp,
        stderr=log_fp,
        creationflags=creationflags
    )

    for _ in range(30):
        time.sleep(0.15)
        if is_server_running():
            print(json.dumps({"status": "started", "pid": proc.pid, "url": "http://127.0.0.1:7357"}))
            return

    print(json.dumps({"status": "error", "message": "Failed to start server. Check server.log"}))

if __name__ == "__main__":
    start_server()
