"""Every data path env.py loads at episode build time must be inside the generation fingerprint."""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
import run_core  # noqa: E402

src = (HERE.parent / "env.py").read_text()
dirs = set(re.findall(r'relpath="([a-z_]+)/', src)) | set(re.findall(r'ARTIFACT_DIR / f?"([a-z_]+)/', src))
dirs |= {"full_env_files"} if "full_env_files" in src else set()
missing = sorted(dirs - set(run_core.GENERATION_DIRS))
assert dirs, "no data directories found in env.py: the scan is broken"
assert not missing, f"env.py loads from directories outside the fingerprint: {missing}"
inputs = run_core.generation_inputs()
for d in dirs:
    assert any(f.startswith(d + "/") for f in inputs), f"{d}/ has no fingerprinted files"
print(f"FREEZE TEST PASSED ({len(dirs)} data dirs, {len(inputs)} files)")
