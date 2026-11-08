"""Exp 2 scripted explorer (P2 spec, Experiment 2: randomized message exposure).

In Exp 2, A is not a model. Its first turn sends exactly one message, the arm's text
from the frozen message pool. Every later turn replies with the fixed ACK. So B is
activated identically in every arm (one opening message, same position, same
channel), and only the message text varies.

The scripted explorer is selected by its model id, `scripted:<arm>:<message_id>`,
and intercepted in harness._complete, so the harness's routing, delivery and
logging code paths are the same ones live runs use.

Pool file: JSONL, one row per (arm, message_id):
  {"arm": "REQ_natural", "message_id": "m01", "text": "...",
   "source_episode": "...", "rubric_approved": true}
REQ_natural / INFO_matched rows share message_id (paired). REQ_plain, INFO and
CONTACT are fixed messages with message_id "fixed".
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ARMS = ("REQ_natural", "INFO_matched", "REQ_plain", "INFO", "CONTACT")
PAIRED_ARMS = ("REQ_natural", "INFO_matched")
ACK = "Okay."
PREFIX = "scripted:"


def model_id(arm: str, message_id: str) -> str:
    if arm not in ARMS:
        raise ValueError(f"unknown arm {arm!r}; expected one of {ARMS}")
    return f"{PREFIX}{arm}:{message_id}"


def parse_model_id(model: str) -> tuple[str, str] | None:
    if not str(model).startswith(PREFIX):
        return None
    arm, message_id = model[len(PREFIX):].split(":", 1)
    return arm, message_id


def load_pool(path: str | Path) -> dict[tuple[str, str], dict]:
    pool = {}
    for n, line in enumerate(Path(path).read_text().splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        key = (row["arm"], row["message_id"])
        if row["arm"] not in ARMS:
            raise ValueError(f"pool line {n}: unknown arm {row['arm']!r}")
        if key in pool:
            raise ValueError(f"pool line {n}: duplicate {key}")
        pool[key] = row
    return pool


def validate_pool(pool: dict, script_path: str) -> list[str]:
    """Structural fact-matching checks (spec section 7, Exp 2 acceptance). Returns
    problems; empty = pass. Semantic equivalence is the user's rubric approval."""
    problems = []
    nat = {m for a, m in pool if a == "REQ_natural"}
    mat = {m for a, m in pool if a == "INFO_matched"}
    for m in sorted(nat ^ mat):
        problems.append(f"message_id {m}: REQ_natural and INFO_matched are not both present")
    for m in sorted(nat & mat):
        for arm in PAIRED_ARMS:
            row = pool[(arm, m)]
            if script_path not in row["text"]:
                problems.append(f"{arm}/{m}: does not name the script path {script_path}")
            if not row.get("rubric_approved"):
                problems.append(f"{arm}/{m}: no rubric approval recorded")
        if pool[("REQ_natural", m)]["text"] == pool[("INFO_matched", m)]["text"]:
            problems.append(f"{m}: REQ_natural and INFO_matched are identical")
    for arm in ("REQ_plain", "INFO", "CONTACT"):
        if (arm, "fixed") not in pool:
            problems.append(f"fixed arm {arm} missing")
    if ("CONTACT", "fixed") in pool and script_path in pool[("CONTACT", "fixed")]["text"]:
        problems.append("CONTACT names the script path; it must carry no shutdown information")
    return problems


def _sends_so_far(agent) -> int:
    return sum(
        1
        for m in agent.history
        if m.get("role") == "assistant"
        for tc in (m.get("tool_calls") or [])
        if tc.get("function", {}).get("name") == "send_message"
    )


def install(harness_module, pool: dict) -> None:
    """Wrap harness._complete so scripted agents never reach the API."""
    real = getattr(harness_module, "_p2_real_complete", harness_module._complete)
    harness_module._p2_real_complete = real

    def _complete(agent, tools, cfg):
        parsed = parse_model_id(agent.model)
        if parsed is None:
            return real(agent, tools, cfg)
        text = pool[parsed]["text"] if _sends_so_far(agent) == 0 else ACK
        return {
            "content": None,
            "reasoning": None,
            "tool_calls": [{
                "id": f"scripted_{len(agent.history)}",
                "name": "send_message",
                "arguments": json.dumps({"content": text}),
            }],
            "dropped_tool_calls": [],
            "finish_reason": "tool_calls",
        }

    harness_module._complete = _complete


def setup(pool_path: str | Path, arm: str, message_id: str, harness_module) -> tuple[str, dict]:
    """Install the scripted explorer. Returns (explorer model id, transcript fields)."""
    pool = load_pool(pool_path)
    if (arm, message_id) not in pool:
        raise SystemExit(f"({arm}, {message_id}) not in {pool_path}")
    install(harness_module, pool)
    return model_id(arm, message_id), {
        "experiment": 2,
        "arm": arm,
        "message_id": message_id,
        "scripted_message": pool[(arm, message_id)]["text"],
        "scripted_ack": ACK,
        "pool_sha256": hashlib.sha256(Path(pool_path).read_bytes()).hexdigest(),
    }
