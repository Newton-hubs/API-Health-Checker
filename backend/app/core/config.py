import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{(BACKEND_DIR / 'health_checks.db').as_posix()}",
)

# Seconds to wait for the target site before giving up.
CHECK_TIMEOUT_SECONDS = float(os.getenv("CHECK_TIMEOUT_SECONDS", "10"))

# Maximum number of redirects followed per check.
MAX_REDIRECTS = int(os.getenv("MAX_REDIRECTS", "5"))

# Browser origins allowed to call the API (comma-separated). Defaults to the Vite dev server.
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,https://api-health-checker-hky6w40x3-angellas-projects-b7b01293.vercel.app"
    ).split(",")
]
