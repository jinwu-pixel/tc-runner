from pathlib import Path
import sys


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIR))


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]
