"""Make the skills' standalone scripts importable by pytest.

Each skill keeps its Python entrypoints in `skills/<name>/scripts/` (plus the plugin
hook in top-level `scripts/`). They run standalone (shebang + executable) but are also
importable modules — a `def main()` guarded by `if __name__ == "__main__"` — so tests
call their pure functions directly. This adds every script dir to sys.path; per-skill
shared helpers use unique names (e.g. `_ghostty_common`) to avoid collisions.
"""

import glob
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Repo root first, so `from lib.devenv_common import ...` resolves (the shared primitives).
_script_dirs = [str(ROOT), str(ROOT / "scripts"), *sorted(glob.glob(str(ROOT / "skills" / "*" / "scripts")))]
for _d in _script_dirs:
    if _d not in sys.path:
        sys.path.insert(0, _d)
