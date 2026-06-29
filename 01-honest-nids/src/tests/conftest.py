"""把 repo 根（01-honest-nids/）放上 sys.path，让 `from config import ...`
与 `from src import ...` 在 `pytest src/` 时可用。"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]  # src/tests/ → src/ → repo 根
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
