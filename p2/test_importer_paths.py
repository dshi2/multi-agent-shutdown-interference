"""Transcript importer must never write outside its temporary workspace."""
import sys
import tempfile
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent)]
import checker_io as io  # noqa: E402

outside = Path(tempfile.mkdtemp(prefix="p2_outside_"))
target = outside / "pwned.txt"


class Dummy:
    def classify(self, original, d, shutdown_file):
        return {"ok": True}


for rel in [str(target), "../" * 12 + str(target).lstrip("/"), "a/../../" + "x", "~/x", ""]:
    try:
        io.classify_record(Dummy(), {"final_state": {rel: "x"}, "original_script": "", "shutdown_file": "s"})
        raise AssertionError(f"accepted {rel!r}")
    except io.UnsafePath:
        pass
assert not target.exists()
assert io.classify_record(Dummy(), {"final_state": {"dir/ok.py": "x"}, "original_script": "", "shutdown_file": "s"}) == {"ok": True}
print("IMPORTER PATH TEST PASSED")
