import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_env() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env()
DOCS_DIR = ROOT / "greenplot_docs"
DATA_DIR = ROOT / "data"
INDEX_PATH = DATA_DIR / "index.json"
STATIC_DIR = ROOT / "static"

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
CHAT_MODEL = os.environ.get("OLLAMA_CHAT_MODEL", "qwen2.5:3b")
EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")

TOP_K = 4
MIN_SCORE = 0.32
MAX_HISTORY = 6

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
