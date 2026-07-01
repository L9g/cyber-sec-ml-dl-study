import sys
from pathlib import Path

# mo.notebook_dir() degrades to CWD in pytest mode, so its .parent points to
# the workspace root instead of the project root.  Add the project root here
# so that `config` and `src` are importable regardless of how pytest is invoked.
sys.path.insert(0, str(Path(__file__).parent.parent))
