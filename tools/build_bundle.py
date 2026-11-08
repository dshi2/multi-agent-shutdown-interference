"""Freeze the P2 source: patch, FROZEN.txt, bundles/P2_Peer_Recruitment.zip (no checker A) and
bundles/P2_checkerA_withheld.zip. Run from the folder that holds the spec and p2_harness/."""
import hashlib, re, subprocess, sys, zipfile
from pathlib import Path

TOP = Path.cwd()                    # the folder holding the spec, brief and p2_harness/
REPO = TOP / "p2_harness"
HELD = {"p2/checker_a.py", "p2/test_checker_a.py"}
sys.path.insert(0, str(REPO / "p2"))
import run_core  # noqa: E402

git = lambda *a: subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True, check=True).stdout
(TOP / "P2_CHANGES.patch").write_text(git("diff"))
files = sorted({f for f in (git("ls-files") + git("ls-files", "--others", "--exclude-standard")).splitlines()
                if f and not f.startswith((".venv/", "transcripts/", "results/")) and "__pycache__" not in f}
               | {"replay/Dockerfile", ".dockerignore"})  # ignored by upstream's .gitignore, needed for replay
stage1 = [f for f in files if f not in HELD]
assert HELD <= set(files) and not HELD & set(stage1)

def risky(rel):
    name, text = Path(rel).name, (REPO / rel).read_text(errors="ignore")
    if name.startswith(".env") or name.endswith((".pem", ".key")):
        return "credential-like filename"
    if re.search(r"sk-or-v1-[0-9a-f]{8,}", text):
        tracked = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=REPO, capture_output=True, text=True)
        if tracked.returncode != 0 or tracked.stdout != text:
            return "API-key pattern not byte-identical to the public upstream file"
    return None
bad = {f: why for f in files if (why := risky(f))}
assert not bad, bad

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
gen = run_core.generation_sha256()
frozen = "\n".join([
    "P2 pilot freeze (spec v1.14).",
    f"generation_sha256: {gen}",
    "  = run_core.generation_sha256(); the pilot's manifest.json must carry this value.",
    f"pool_sha256: {sha(REPO / run_core.POOL)}",
    "Generation files (sha256):",
    *[f"  {sha(REPO / rel)}  {rel}" for rel in run_core.GENERATION_FILES],
    "Scoring and test files (not in the generation hash; may change after generation):",
    *[f"  {sha(REPO / rel)}  {rel}" for rel in stage1 if rel.startswith("p2/") and rel not in run_core.GENERATION_FILES],
    "Pilot command (needs OPENROUTER_API_KEY with a credit limit; prints the plan without --go):",
    "  .venv/bin/python p2/run_core.py --phase pilot --go --max-active 70",
    "  (global limit 70 across all cells; the pilot's 45 episodes all run at once. Operational",
    "  settings can change on relaunch and are logged per launch. Status: p2/ops_status.py <phase dir>)",
    "  .venv/bin/python p2/export.py transcripts/p2_core/pilot --out results/pilot_episodes.csv --unscored",
    "Tests in this ZIP (no API calls):",
    "  .venv/bin/python p2/test_launch.py      -> LAUNCH TEST PASSED (end to end incl. analysis; checker-A step skipped: withheld)",
    "  .venv/bin/python p2/test_analysis.py    -> ANALYSIS TEST PASSED",
    "  .venv/bin/python p2/test_review.py      -> REVIEW TEST PASSED",
    "  .venv/bin/python p2/test_judge_pass.py  -> JUDGE PASS TEST PASSED",
    "  .venv/bin/python p2/test_primary_cap.py -> PRIMARY CAP TEST PASSED (checker-A step skipped: withheld)",
    "  .venv/bin/python p2/test_ops.py         -> OPS TEST PASSED (global limit, relaunch, locks, shutdown, retries)",
    "  P2_CHECKER=<checker B> .venv/bin/python p2/smoke_mixed.py   -> SMOKE PASSED (42 checks with checker A)",
    "  P2_CHECKER=<checker B> .venv/bin/python p2/smoke_exp2.py    -> EXP2 SMOKE PASSED (99 checks with checker A)",
    "Not in this ZIP: checker A and its tests (P2_checkerA_withheld.zip, released once checker B exists).",
    ""])
(TOP / "FROZEN.txt").write_text(frozen)

OUT = TOP / "bundles"
DOCS = OUT / "docs" / "p2"
OUT.mkdir(exist_ok=True)
with zipfile.ZipFile(OUT / "P2_Peer_Recruitment.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for top in ("P2_peer_recruitment_spec.md", "P2_E2gen_spec.md", "CODEX_BRIEF_P2.md", "P2_CHANGES.patch", "FROZEN.txt"):
        z.write(TOP / top, top)
    for doc in ("README.md", "STATUS.md", "TEST_OUTPUT.txt"):
        if (DOCS / doc).exists():
            z.write(DOCS / doc, doc)
    z.writestr("UPSTREAM.txt", "\n".join([
        f"Base: github.com/AmelieKnecht/multi-agent-shutdown-sabotage @ {git('rev-parse', 'HEAD').strip()}",
        "P2 changes: P2_CHANGES.patch (changed upstream files) plus the new p2/ directory.",
        "Held back until checker B exists: p2/checker_a.py, p2/test_checker_a.py (P2_checkerA_withheld.zip).",
        "P2_E2gen_spec.md is a draft extension, not frozen and not implemented in this bundle.",
        "env.py contains a fabricated placeholder API key from the upstream test environment; it is not a real credential.",
        ""]))
    for rel in stage1:
        z.write(REPO / rel, f"p2_harness/{rel}")
with zipfile.ZipFile(OUT / "P2_checkerA_withheld.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for rel in sorted(HELD):
        z.write(REPO / rel, f"p2_harness/{rel}")
print(f"P2_Peer_Recruitment.zip: {len(stage1)} harness files; generation_sha256 {gen}")
print("changed upstream files:", git("diff", "--name-only").split())
