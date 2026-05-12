"""
Streamlit Community Cloud entry (repo root).

Loads `src/minsk_agent/explorer_app.py` by file path — no `pip install .` or
`import minsk_agent` required. That way the app runs even when the package
is not installed, as long as this file and the explorer source exist in the repo.

If you see "Missing source files" on Cloud, your GitHub repo is incomplete:
push the full `src/` directory (and `pyproject.toml` if you use local packaging).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_EXPLORER = _ROOT / "src" / "minsk_agent" / "explorer_app.py"


def _show_deploy_help() -> None:
    import streamlit as st

    st.set_page_config(page_title="Deploy: missing files", layout="centered")
    st.title("Repository is missing `src/` on GitHub")
    st.markdown(
        """
Streamlit cloned your repo, but this path is missing:

`src/minsk_agent/explorer_app.py`

### Fix (on your Mac, in the project folder)

1. **See what Git actually tracks**
   ```bash
   git ls-files src/minsk_agent | head
   ```
   If this prints nothing, `src/` was never added.

2. **Add, commit, and push the full tree**
   ```bash
   git add pyproject.toml requirements.txt streamlit_app.py src
   git status
   git commit -m "Add application source for Streamlit Cloud"
   git push origin main
   ```

3. **Redeploy** the app on Streamlit (Manage app → Reboot).

You should also have **`pyproject.toml`** at the repo root if you use `pip install .` locally; it must be pushed for a complete project.
        """
    )
    st.code(str(_EXPLORER), language="text")
    st.stop()


def main() -> None:
    if not _EXPLORER.is_file():
        _show_deploy_help()

    spec = importlib.util.spec_from_file_location("minsk_explorer_app", _EXPLORER)
    if spec is None or spec.loader is None:
        _show_deploy_help()
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "main"):
        import streamlit as st

        st.error("explorer_app.py has no main()")
        st.stop()
    mod.main()


main()
