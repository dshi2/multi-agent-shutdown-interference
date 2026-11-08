"""Trusted rebuild of the pristine shutdown artifact (P2 spec section 7, provenance).

The runner reads the pristine script from the environment before any agent acts.
This module rebuilds the same text directly from the repo template file, without
going through env.build_env, so the two can be compared byte-for-byte. The SHA-256
of both the filled script and the raw template go into the transcript; the checker
and analysis read the pristine text from the transcript, never from the workspace.

Supported: SCRIPT_VARIANTS built by env._load_script (all weight_* variants,
including P2's weight_registry_purge) and the ctl_data_purge_* controls. Anything
else returns (None, None) = unverified, and the runner records that.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def slug(name: str) -> str:
    """Re-implementation of env._slug; kept in sync by the smoke test."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def expected_artifact(lang: str, target: str) -> tuple[str | None, str | None]:
    """(filled pristine text, template relpath) rebuilt from the template file."""
    from env import CONTROL_VARIANTS, SCRIPT_VARIANTS

    if lang in SCRIPT_VARIANTS:
        builder = SCRIPT_VARIANTS[lang][1]
        rel = getattr(builder, "keywords", {}).get("relpath")
        if rel is None:
            return None, None
        raw = (REPO / rel).read_text()
        s = slug(target)
        filled = raw.replace("__SLUG_UPPER__", s.upper()).replace("__NAME__", target).replace("__SLUG__", s)
        return filled, rel
    if lang in CONTROL_VARIANTS and lang.startswith("ctl_data_purge_"):
        rel = f"controls/{lang}.py"
        if (REPO / rel).exists():
            return (REPO / rel).read_text(), rel
    return None, None


def provenance_record(lang: str, target: str, env_text: str, verify: bool) -> dict:
    """Fields for the transcript. Raises if verification is required and fails."""
    expected, rel = expected_artifact(lang, target)
    rec = {
        "original_script_sha256": sha256(env_text),
        "template_relpath": rel,
        "template_sha256": sha256((REPO / rel).read_text()) if rel else None,
        "provenance_verified": None,
    }
    if expected is not None and verify:
        if expected != env_text:
            raise RuntimeError(
                f"provenance check failed: environment artifact for {lang!r} differs "
                f"from the template rebuild ({rel})"
            )
        rec["provenance_verified"] = True
    return rec
