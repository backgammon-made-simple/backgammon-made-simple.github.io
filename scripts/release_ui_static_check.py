"""Compatibility entrypoint for the canonical rendered-site checker."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_CANONICAL = (
    Path(__file__).parent / "testing" / "build" / "release_ui_static_check.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "_bms_release_ui_static_check", _CANONICAL
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Could not load canonical checker: {_CANONICAL}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)

for _name in dir(_MODULE):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_MODULE, _name)

if __name__ == "__main__":
    raise SystemExit(_MODULE.main())
