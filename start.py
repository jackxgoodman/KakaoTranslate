"""Launcher used by run.bat / Task Scheduler: runs the version chosen by AUTOSTART_VERSION in config."""

import runpy
import sys
from pathlib import Path

from config import AUTOSTART_VERSION

_SCRIPTS = {1: 'main.py', 2: 'main_v2.py', 3: 'main_v3.py'}

script = _SCRIPTS.get(int(AUTOSTART_VERSION))
if script is None:
    sys.exit(f"AUTOSTART_VERSION must be 1, 2 or 3 (got {AUTOSTART_VERSION!r})")
runpy.run_path(str(Path(__file__).parent / script), run_name='__main__')
