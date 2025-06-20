import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

BASE = os.getenv("BASE", "/home/root")
PATH_TO_REPL = os.getenv("PATH_TO_REPL", f"{BASE}/repl/.lake/build/bin/repl")

# TODO: Make mathlib optional (but default to true)
PATH_TO_MATHLIB = os.getenv("PATH_TO_MATHLIB", f"{BASE}/mathlib4")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
