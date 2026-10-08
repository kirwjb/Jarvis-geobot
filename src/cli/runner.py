"""
Unified Runner and Process Orchestrator for JARVIS GeoBot.

Runs via:
    Jarvis -r
    python jarvis.py -r

Features:
- Launches backend (FastAPI + AsyncTeleBot) and ngrok concurrently.
- Queries ngrok local client API (http://127.0.0.1:4040/api/tunnels) for the public HTTPS URL.
- Prints clear URLs and dashboard status.
- Graceful shutdown on Ctrl+C (SIGINT / SIGTERM) cleaning up all child processes.
"""

import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


def find_ngrok_binary() -> str | None:
    """Find ngrok executable on PATH or common macOS/Linux locations."""
    which_ngrok = shutil.which("ngrok")
    if which_ngrok:
        return which_ngrok

    common_paths = [
        "/usr/local/bin/ngrok",
        "/opt/homebrew/bin/ngrok",
        Path.home() / ".local" / "bin" / "ngrok",
        Path.home() / "bin" / "ngrok",
    ]
    for p in common_paths:
        if os.path.exists(p) and os.access(p, os.X_OK):
            return str(p)
    return None


def fetch_ngrok_public_url(timeout_secs: float = 8.0) -> str | None:
    """Poll ngrok's local management API for the active public HTTPS tunnel."""
    start_time = time.time()
    api_url = "http://127.0.0.1:4040/api/tunnels"

    while time.time() - start_time < timeout_secs:
        try:
            req = urllib.request.Request(api_url, headers={"User-Agent": "JARVIS-Runner"})
            with urllib.request.urlopen(req, timeout=1.0) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    tunnels = data.get("tunnels", [])
                    # Look for HTTPS tunnel first
                    for t in tunnels:
                        public_url = t.get("public_url", "")
                        if public_url.startswith("https://"):
                            return public_url
                    if tunnels:
                        return tunnels[0].get("public_url")
        except Exception:
            time.sleep(0.5)
    return None


def free_port_if_occupied(port: int = 8000) -> None:
    """Check if the target port is in use and gracefully terminate stale backend processes."""
    try:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return  # Port is free

        print(f"{YELLOW}⚠️  Port {port} is currently in use. Cleaning up stale process...{RESET}")
        cmd = ["lsof", "-ti", f":{port}"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        pids = [p.strip() for p in res.stdout.split() if p.strip()]
        for pid in pids:
            try:
                pid_int = int(pid)
                if pid_int != os.getpid():
                    os.kill(pid_int, signal.SIGTERM)
                    time.sleep(0.5)
                    try:
                        os.kill(pid_int, signal.SIGKILL)
                    except OSError:
                        pass
            except Exception:
                pass
        time.sleep(0.5)
    except Exception as exc:
        print(f"{DIM}Note on port check: {exc}{RESET}")


def run_services(host: str = "0.0.0.0", port: int = 8000, mock_auth: bool = False):
    """Launch backend and ngrok concurrently with graceful shutdown."""
    print(f"""{CYAN}{BOLD}
╔══════════════════════════════════════════════════════════════╗
║               🗺️  JARVIS SYSTEM RUNNER                       ║
║        FastAPI · AsyncTeleBot · Mini App · ngrok             ║
╚══════════════════════════════════════════════════════════════╝{RESET}""")

    # Check and free port 8000 if a zombie instance is still listening
    free_port_if_occupied(port)

    processes: list[subprocess.Popen] = []

    def clean_exit(signum=None, frame=None):
        print(f"\n{YELLOW}Received termination signal. Shutting down gracefully...{RESET}")
        for p in processes:
            if p.poll() is None:
                try:
                    # Terminate process group if available
                    pgid = os.getpgid(p.pid)
                    os.killpg(pgid, signal.SIGINT)
                except Exception:
                    try:
                        p.send_signal(signal.SIGINT)
                    except Exception:
                        pass

        # Give up to 3 seconds for clean shutdown
        stop_time = time.time()
        for p in processes:
            while p.poll() is None and (time.time() - stop_time < 3.0):
                time.sleep(0.1)
            if p.poll() is None:
                try:
                    pgid = os.getpgid(p.pid)
                    os.killpg(pgid, signal.SIGKILL)
                except Exception:
                    try:
                        p.kill()
                    except Exception:
                        pass

        print(f"{GREEN}All JARVIS services stopped cleanly.{RESET}")
        sys.exit(0)

    signal.signal(signal.SIGINT, clean_exit)
    signal.signal(signal.SIGTERM, clean_exit)
    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, clean_exit)

    # 1. Start Backend process
    backend_script = str(ROOT_DIR / "main_combined.py")
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PORT"] = str(port)
    if mock_auth or os.getenv("MOCK_AUTH") == "1":
        env["MOCK_AUTH"] = "1"
        env["JARVIS_MOCK_AUTH"] = "1"

    print(f"{DIM}Starting backend server ({backend_script}) on port {port}...{RESET}")
    backend_proc = subprocess.Popen(
        [sys.executable, backend_script],
        cwd=str(ROOT_DIR),
        env=env,
        preexec_fn=os.setsid if hasattr(os, "setsid") else None,
    )
    processes.append(backend_proc)

    # 2. Check existing ngrok or launch a new ngrok process
    existing_url = fetch_ngrok_public_url(timeout_secs=1.5)
    ngrok_url = None

    if existing_url:
        print(f"{GREEN}Reusing existing active ngrok tunnel:{RESET} {existing_url}")
        ngrok_url = existing_url
    else:
        ngrok_bin = find_ngrok_binary()
        if ngrok_bin:
            print(f"{DIM}Starting ngrok tunnel via {ngrok_bin} on port {port}...{RESET}")
            ngrok_proc = subprocess.Popen(
                [ngrok_bin, "http", str(port), "--host-header=rewrite", "--log=stdout"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=str(ROOT_DIR),
                preexec_fn=os.setsid if hasattr(os, "setsid") else None,
            )
            processes.append(ngrok_proc)
            print(f"{DIM}Connecting to ngrok tunnel API...{RESET}")
            ngrok_url = fetch_ngrok_public_url(timeout_secs=7.0)
        else:
            print(f"{YELLOW}⚠️  ngrok binary not found on PATH. Backend running locally without tunnel.{RESET}")
            print(f"{DIM}   To enable public tunnels, install ngrok: brew install ngrok{RESET}")

    # 3. Print Dashboard
    print(f"\n{GREEN}{BOLD}✅ JARVIS SERVICES ONLINE{RESET}")
    print(f" • Local Backend:    {CYAN}http://127.0.0.1:{port}{RESET}")
    if ngrok_url:
        print(f" • ngrok HTTPS URL:  {BOLD}{GREEN}{ngrok_url}{RESET}")
        print(f" • Telegram MiniApp: {BOLD}{CYAN}{ngrok_url}{RESET}")
    if mock_auth or os.getenv("MOCK_AUTH") == "1":
        print(f" • Auth Mode:        {BOLD}{YELLOW}🔓 MOCK AUTH ACTIVE (--auth=0; signatures bypassed){RESET}")
    print(f" • Bot Status:       {GREEN}AsyncTeleBot Polling Active{RESET}")

    print(f"\n{DIM}[Press Ctrl+C at any time to gracefully terminate all services]{RESET}\n")

    # Monitor backend process
    try:
        while True:
            status = backend_proc.poll()
            if status is not None:
                print(f"{RED}Backend process terminated with code {status}.{RESET}")
                clean_exit()
            time.sleep(0.5)
    except KeyboardInterrupt:
        clean_exit()
