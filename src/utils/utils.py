import sys
import logging
from logging.handlers import RotatingFileHandler
import os



GREEN = "\033[95m"
RED = "\033[31m"
PURPLE = "\033[35m"
RESET = "\033[0m"

# --- PART TIME LOCAL LOGGING FEATURES, RECOMMENDED FOR DEVELOPMENT ---
def log(msg):
    print(f"{GREEN}[LOG] {msg}{RESET}", flush=True)

def error(msg):
    print(f"{RED}[ERROR] {msg}{RESET}", file=sys.stderr, flush=True)

def info(msg):
    print(f"{PURPLE}[INFO] {msg}{RESET}", flush=True)

#--- SETUP ROTATING FILE HANDLER FOR LOGGING, RECOMENDED FOR WORK ---

if not os.path.exists("logs"):
    os.makedirs("logs")

log_formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

file_handler = RotatingFileHandler(
    filename="logs/bot.log", 
    mode="a", 
    maxBytes=5*1024*1024, 
    backupCount=5, 
    encoding="utf-8"
)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)



logger = logging.getLogger("JARVIS_GEO")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)

#--- SETUP ROTATING FILE HANDLER FOR ADMIN LOGGING, RECOMENDED FOR WORK ---
if not os.path.exists("logs"):
    os.makedirs("logs")

admin_logger = logging.getLogger("JARVIS_ADMIN")
admin_file_handler = RotatingFileHandler(
    filename="logs/admin.log", 
    mode="a", 
    maxBytes=5*1024*1024, 
    backupCount=5, 
    encoding="utf-8"
)
admin_file_handler.setFormatter(log_formatter)
admin_file_handler.setLevel(logging.INFO)
admin_logger.setLevel(logging.INFO)
admin_logger.addHandler(admin_file_handler)