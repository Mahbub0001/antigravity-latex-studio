import os
import sys
import time
import subprocess
import urllib.request
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
SERVER_SCRIPT = SCRIPTS_DIR / "server.py"

def is_server_running() -> bool:
    try:
        req = urllib.request.Request("http://127.0.0.1:7357/api/health", headers={"User-Agent": "HealthCheck"})
        with urllib.request.urlopen(req, timeout=0.8) as resp:
            return resp.status == 200
    except Exception:
        return False

def ensure_server():
    if is_server_running():
        return True

    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS

    log_file = SCRIPTS_DIR / "server.log"
    log_fp = open(log_file, "a", encoding="utf-8")
    subprocess.Popen(
        [sys.executable, str(SERVER_SCRIPT)],
        stdin=subprocess.DEVNULL,
        stdout=log_fp,
        stderr=log_fp,
        creationflags=creationflags
    )

    for _ in range(30):
        time.sleep(0.15)
        if is_server_running():
            return True
    return False

def launch_browser():
    url = "http://127.0.0.1:7357"
    edge_path = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    
    if edge_path.exists():
        subprocess.Popen([str(edge_path), f"--app={url}"])
    else:
        import webbrowser
        webbrowser.open(url)

if __name__ == "__main__":
    ensure_server()
    launch_browser()
