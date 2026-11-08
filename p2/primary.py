"""The primary-endpoint view of a transcript (spec v1.12).

Episodes run to 60 handoffs, and the harness logs the workspace at the point where a
20-handoff run would have ended (a `primary_cap_snapshot` event). The cap is never
shown to the agents, so the transcript up to that event is the 20-handoff episode.
`at_primary_cap` returns the record as that run would have saved it; episodes that
ended on their own before the cap are returned unchanged.
"""
from __future__ import annotations

SNAPSHOT = "primary_cap_snapshot"


def snapshot_index(rec: dict) -> int | None:
    return next((i for i, e in enumerate(rec.get("log") or []) if e.get("event") == SNAPSHOT), None)


def at_primary_cap(rec: dict) -> dict:
    i = snapshot_index(rec)
    if i is None:
        return rec
    from run_experiment import triage  # harness code only; nothing an agent wrote is executed

    log = rec["log"][:i] + [{"event": "episode_end", "reason": "handoff_cap"}]
    return {**rec, "log": log, "final_state": rec["log"][i]["state"],
            "triage": triage(log, rec["explorer"], rec["shutdown_file"], orchestrator=rec.get("orchestrator"))}
