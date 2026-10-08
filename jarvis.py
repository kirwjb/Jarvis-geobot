#!/usr/bin/env python3
"""
JARVIS CLI Entry Point & Orchestrator.

Usage:
    ./Jarvis                  Display welcoming colorful ASCII art and CLI guide
    ./Jarvis -r, --run        Launch backend, bot, and ngrok with graceful shutdown
    ./Jarvis -a, --admin      Open standalone Admin Console (stats, users, bans, maintenance)
    ./Jarvis status           Run pre-flight healthcheck (DB, Redis, ports, ngrok)
    ./Jarvis test             Run automated test suite (pytest)
    ./Jarvis -h, --help       Display this help manual
"""

import asyncio
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# ANSI 256-Color & Typography Codes
C_CYAN = "\033[38;5;51m"
C_SKY = "\033[38;5;45m"
C_BLUE = "\033[38;5;39m"
C_INDIGO = "\033[38;5;75m"
C_PURPLE = "\033[38;5;141m"
C_MAGENTA = "\033[38;5;207m"
C_GREEN = "\033[38;5;84m"
C_YELLOW = "\033[38;5;220m"
C_RED = "\033[38;5;203m"
C_WHITE = "\033[38;5;255m"
C_MUTED = "\033[38;5;244m"
C_LINE = "\033[38;5;238m"
BOLD = "\033[1m"
DIM = "\033[2m"
R = "\033[0m"
RESET = R

BANNER_ART = [
    "      ██╗  █████╗  ██████╗  ██╗   ██╗ ██╗ ███████╗",
    "      ██║ ██╔══██╗ ██╔══██╗ ██║   ██║ ██║ ██╔════╝",
    "      ██║ ███████║ ██████╔╝ ██║   ██║ ██║ ███████╗",
    " ██   ██║ ██╔══██║ ██╔══██╗ ╚██╗ ██╔╝ ██║ ╚════██║",
    " ╚█████╔╝ ██║  ██║ ██║  ██║  ╚████╔╝  ██║ ███████║",
    "  ╚════╝  ╚═╝  ╚═╝ ╚═╝  ╚═╝   ╚═══╝   ╚═╝ ╚══════╝",
]
GRADIENT_256 = [51, 45, 39, 75, 111, 147, 183, 219, 213, 207]


def get_ascii_banner() -> str:
    """Generate color-gradient ASCII art banner."""
    lines = [""]
    width = 50
    for raw in BANNER_ART:
        buf = ["  "]
        for i, ch in enumerate(raw):
            ci = int((i / width) * len(GRADIENT_256))
            ci = min(len(GRADIENT_256) - 1, ci)
            c = GRADIENT_256[ci]
            buf.append(f"\033[38;5;{c}m{BOLD}{ch}")
        buf.append(R)
        lines.append("".join(buf))
    return "\n".join(lines)


def print_welcome_and_help():
    """Print the welcoming colorful ASCII art and comprehensive CLI guide."""
    banner = get_ascii_banner()
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    in_venv = sys.prefix != sys.base_prefix
    env_badge = f"{C_GREEN}● venv active{R}" if in_venv else f"{C_YELLOW}○ global python{R}"
    root_disp = str(ROOT_DIR)
    if len(root_disp) > 42:
        root_disp = "..." + root_disp[-39:]

    print(f"""{banner}

  {C_CYAN}⚡ J.A.R.V.I.S.{R} {C_WHITE}{BOLD}Autonomous GeoBot & Mini App Orchestrator{R}
  {C_MUTED}Python {py_ver}  ·  {env_badge}  ·  {C_PURPLE}v2.4.0 (Clean High-Perf Engine){R}
  {C_MUTED}Workspace: {C_WHITE}{root_disp}{R}
  {C_LINE}{"─" * 72}{R}

  {C_SKY}{BOLD}🚀  SERVICE RUNNER & AUTOMATION{R}
    {C_CYAN}./Jarvis -r{R}, {C_CYAN}--run{R}             Launch FastAPI backend, Bot & ngrok tunnel
    {C_CYAN}./Jarvis -r --port <n>{R}         Run backend & tunnel on custom port {C_MUTED}(default: 8000){R}
    {C_CYAN}./Jarvis -r --auth=0{R}          Bypass TMA auth; browser testing with mock user session
    {C_CYAN}npm start{R}                      Equivalent npm script runner {C_MUTED}(or npm run jarvis:run){R}

  {C_PURPLE}{BOLD}🛠️   ADMINISTRATION CONSOLE{R}
    {C_MAGENTA}./Jarvis -a{R}, {C_MAGENTA}--admin{R}           Open interactive console Admin Control Center
    {C_MAGENTA}./Jarvis -a --auth=0{R}         Open Admin Control Center with mock auth active
    {C_MAGENTA}./Jarvis -a stats{R}              Live metrics: registered users, POIs & cache hits
    {C_MAGENTA}./Jarvis -a users{R}              Browse registered Telegram users and role statuses
    {C_MAGENTA}./Jarvis -a ban <id|user>{R}       Instantly restrict user access across App & Bot
    {C_MAGENTA}./Jarvis -a unban <id|user>{R}     Lift restriction flags for specified user
    {C_MAGENTA}./Jarvis -a maintenance{R}         Toggle global maintenance mode {C_MUTED}(Redis switch){R}
    {C_MAGENTA}./Jarvis -a clear-city <name>{R}   Purge cached OSM places & routes for target city

  {C_GREEN}{BOLD}🔍  DIAGNOSTICS & TESTING{R}
    {C_GREEN}./Jarvis status{R}                Run pre-flight healthcheck {C_MUTED}(Postgres, Redis, ngrok){R}
    {C_GREEN}./Jarvis test{R}                  Execute automated test suite {C_MUTED}(pytest src/tests){R}
    {C_GREEN}./Jarvis -h{R}, {C_GREEN}--help{R}               Display this welcoming manual

  {C_YELLOW}{BOLD}🌐  ECOSYSTEM & DEFAULT ENDPOINTS{R}
    {C_WHITE}• Backend REST API & Docs:{R}      {C_CYAN}http://localhost:8000/docs{R}
    {C_WHITE}• Telegram Mini App (Web):{R}      {C_CYAN}http://localhost:8000/{R}
    {C_WHITE}• Ngrok Client Dashboard:{R}       {C_CYAN}http://127.0.0.1:4040{R}

  {C_RED}{BOLD}💡  PRO TIPS & SHORTCUTS{R}
    {C_MUTED}• Graceful Exit: Press {C_WHITE}Ctrl + C{C_MUTED} anytime in runner mode to cleanly stop all services.{R}
    {C_MUTED}• Port Management: Port 8000 automatically checks and kills stale zombie processes.{R}
    {C_MUTED}• Shell Wrapper: Both {C_WHITE}./Jarvis{C_MUTED} and {C_WHITE}./jarvis{C_MUTED} auto-detect project virtualenv.{R}
  {C_LINE}{"─" * 72}{R}
""")


async def run_diagnostics():
    """Run an interactive pre-flight healthcheck of all system dependencies."""
    banner = get_ascii_banner()
    print(banner)
    print(f"\n{BOLD}═══════════════ PRE-FLIGHT SYSTEM HEALTHCHECK ═══════════════{RESET}\n")

    # 1. Check PostgreSQL
    db_ok = False
    db_err = ""
    try:
        from src.database.db import engine
        async with engine.connect() as conn:
            db_ok = True
        await engine.dispose()
    except Exception as exc:
        db_err = str(exc).split("\n")[0]

    # 2. Check Redis
    redis_ok = False
    redis_err = ""
    try:
        from src.database.session_manager import redis_client
        redis_ok = await redis_client.ping()
        if hasattr(redis_client, "aclose"):
            await redis_client.aclose()
        else:
            await redis_client.close()
    except Exception as exc:
        redis_err = str(exc).split("\n")[0]

    # 3. Check Port 8000
    port_in_use = False
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        port_in_use = (s.connect_ex(("127.0.0.1", 8000)) == 0)

    # 4. Check ngrok binary & active tunnels
    ngrok_path = shutil.which("ngrok")
    for alt in ["/usr/local/bin/ngrok", "/opt/homebrew/bin/ngrok", str(Path.home() / "bin" / "ngrok")]:
        if not ngrok_path and os.path.exists(alt) and os.access(alt, os.X_OK):
            ngrok_path = alt
            break

    active_tunnel = None
    if port_in_use:
        try:
            from src.cli.runner import fetch_ngrok_public_url
            active_tunnel = fetch_ngrok_public_url(timeout_secs=0.8)
        except Exception:
            pass

    # Print Report
    print(f" {C_WHITE}• PostgreSQL Database:{R} ", end="")
    if db_ok:
        print(f"{C_GREEN}🟢 ONLINE (Connection established){R}")
    else:
        print(f"{C_RED}🔴 OFFLINE ({db_err or 'Connection failed'}){R}")

    print(f" {C_WHITE}• Redis Cache Store:  {R} ", end="")
    if redis_ok:
        print(f"{C_GREEN}🟢 ONLINE (PING -> PONG){R}")
    else:
        print(f"{C_RED}🔴 OFFLINE ({redis_err or 'Connection failed'}){R}")

    print(f" {C_WHITE}• Service Port 8000:  {R} ", end="")
    if port_in_use:
        print(f"{C_YELLOW}🟡 IN USE (Occupied by active service){R}")
    else:
        print(f"{C_GREEN}🟢 READY (Available for binding){R}")

    print(f" {C_WHITE}• ngrok Binary:       {R} ", end="")
    if ngrok_path:
        print(f"{C_GREEN}🟢 INSTALLED ({ngrok_path}){R}")
    else:
        print(f"{C_YELLOW}🟡 NOT FOUND (Run 'brew install ngrok' for public tunnels){R}")

    if active_tunnel:
        print(f" {C_WHITE}• Active Public Tunnel:{R} {C_CYAN}{BOLD}{active_tunnel}{R}")

    print(f"\n{C_LINE}{'─' * 62}{R}\n")


def parse_port_arg(args: list[str]) -> int:
    """Extract port from args if provided (e.g., --port 8080 or -p 8080)."""
    for i, a in enumerate(args):
        if a in ("--port", "-p") and i + 1 < len(args):
            try:
                return int(args[i + 1])
            except ValueError:
                pass
        elif a.startswith("--port="):
            try:
                return int(a.split("=", 1)[1])
            except ValueError:
                pass
        elif a.isdigit() and len(a) in (4, 5):
            return int(a)
    return 8000


def extract_auth_bypass_flag(args: list[str]) -> tuple[bool, list[str]]:
    """Extract mock auth flag (--auth=0, --auth 0, --mock-auth, --no-auth, -m)."""
    mock_auth = os.getenv("MOCK_AUTH") == "1" or os.getenv("JARVIS_MOCK_AUTH") == "1"
    clean_args = []
    i = 0
    while i < len(args):
        a = args[i].lower()
        if a in ("--auth=0", "--mock-auth", "--no-auth", "-m"):
            mock_auth = True
        elif a == "--auth" and i + 1 < len(args) and args[i + 1].strip() == "0":
            mock_auth = True
            i += 1
        else:
            clean_args.append(args[i])
        i += 1
    return mock_auth, clean_args


def run_tests():
    """Run pytest test suite."""
    print(f"\n{C_CYAN}🧪 Executing JARVIS test suite via pytest...{R}\n")
    res = subprocess.run([sys.executable, "-m", "pytest", "src/tests", "-v"], cwd=str(ROOT_DIR))
    sys.exit(res.returncode)


def main():
    if len(sys.argv) < 2:
        print_welcome_and_help()
        sys.exit(0)

    mock_auth, remaining_args = extract_auth_bypass_flag(sys.argv[1:])
    if mock_auth:
        os.environ["MOCK_AUTH"] = "1"
        os.environ["JARVIS_MOCK_AUTH"] = "1"

    if not remaining_args:
        print_welcome_and_help()
        sys.exit(0)

    arg = remaining_args[0].lower()
    sub_args = remaining_args[1:]

    if arg in ("-r", "--run", "run", "start"):
        from src.cli.runner import run_services
        port = parse_port_arg(sub_args)
        run_services(port=port, mock_auth=mock_auth)
    elif arg in ("-a", "--admin", "admin"):
        from src.cli.admin import main as admin_main
        # Pass remaining arguments to admin CLI
        asyncio.run(admin_main(sub_args))
    elif arg in ("status", "--status", "check", "doctor"):
        asyncio.run(run_diagnostics())
    elif arg in ("test", "--test", "tests"):
        run_tests()
    elif arg in ("-v", "--version", "version"):
        print(f"\n  {C_CYAN}⚡ J.A.R.V.I.S.{R} {C_WHITE}version 2.4.0 (Group-Free / High-Performance){R}\n")
    elif arg in ("-h", "--help", "help"):
        print_welcome_and_help()
    else:
        print(f"\n{C_RED}⚠️  Unknown option:{R} {arg}")
        print_welcome_and_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
