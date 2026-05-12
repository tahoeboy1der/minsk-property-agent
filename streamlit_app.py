"""
Streamlit Community Cloud entry point.

Cloud's default main file is often `streamlit_app.py` at the repo root.
This delegates to the real app under `src/`.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from minsk_agent.explorer_app import main  # noqa: E402

main()
