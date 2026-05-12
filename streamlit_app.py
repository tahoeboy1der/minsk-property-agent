"""
Streamlit Community Cloud entry point (repo root).

Cloud runs `pip install -r requirements.txt` which includes `-e .` so `minsk_agent`
is installed. If not, we fall back to adding `src/` to sys.path (nested clone layouts).
"""

from __future__ import annotations

import sys
from pathlib import Path


def _ensure_minsk_agent_on_path() -> None:
    try:
        import minsk_agent  # noqa: F401
    except ModuleNotFoundError:
        pass
    else:
        return

    here = Path(__file__).resolve().parent
    for base in (here, *here.parents):
        src = base / "src"
        init_py = src / "minsk_agent" / "__init__.py"
        if init_py.is_file():
            root_src = str(src)
            if root_src not in sys.path:
                sys.path.insert(0, root_src)
            return

    raise ModuleNotFoundError(
        f"Could not import minsk_agent: no package install and no {here}/src/minsk_agent"
    )


_ensure_minsk_agent_on_path()

from minsk_agent.explorer_app import main  # noqa: E402

main()
