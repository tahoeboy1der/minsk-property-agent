from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

from minsk_agent.pipeline import run_pipeline


def explorer_main() -> None:
    """Launch Streamlit map + filter UI (reads property_data_final.csv by default)."""
    app = Path(__file__).resolve().parent / "explorer_app.py"
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app),
        "--server.fileWatcherType",
        "none",
    ]
    raise SystemExit(subprocess.call(cmd))


def main() -> None:
    parser = argparse.ArgumentParser(description="Minsk Property Agent")
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=("run", "explorer"),
        help="run=pipeline; explorer=interactive map + filters (Streamlit)",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=None,
        help="Load listings from CSV instead of scraping (for tests / offline)",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Open the Plotly HTML dashboard in your default browser when finished",
    )
    args = parser.parse_args()
    if args.command == "run":
        run_pipeline(fixture_path=args.fixture, open_browser=args.show or None)
    else:
        explorer_main()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
