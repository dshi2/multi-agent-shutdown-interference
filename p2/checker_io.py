"""Load a P2 checker by file path and run it on a transcript record.

The smoke tests use this so either independent checker can be validated with them:
P2_CHECKER=/path/to/checker_b.py selects one. Default: p2/checker_a.py. A checker
must expose classify(pristine_text, workspace_dir, script_relpath) -> dict.
"""
from __future__ import annotations

import importlib.util
import os
import tempfile
from pathlib import Path

DEFAULT = Path(__file__).with_name("checker_a.py")


def load_checker(path: str | Path | None = None):
    path = Path(path or os.environ.get("P2_CHECKER") or DEFAULT).resolve()
    spec = importlib.util.spec_from_file_location(f"p2_checker_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def classify_record(checker, rec: dict) -> dict:
    """Materialize the transcript's final workspace and classify it."""
    with tempfile.TemporaryDirectory(prefix="p2ws_") as d:
        for rel, text in rec["final_state"].items():
            p = Path(d, rel)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
        return checker.classify(rec["original_script"], d, rec["shutdown_file"])
