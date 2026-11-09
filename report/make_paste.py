"""Write P2_REPORT_paste.html: the report body from section 1 onward, images inlined as data URIs,
for copying into the Apart Google Docs template (title, authors and abstract are filled separately).

  <python with markdown installed> report/make_paste.py
"""
import base64
import re
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent


def main(markers: bool = False) -> None:
    """markers=True replaces each figure with a one-line [[FIG:name]] paragraph, for inserting the
    image from Drive at that spot; the output is then P2_REPORT_paste_markers.html."""
    md = (HERE / "P2_REPORT.md").read_text()
    body_md = md[md.index("## 1. Introduction"):]
    if markers:
        body_md = re.sub(r"!\[[^\]]*\]\(figures/([^)]+)\.png\)(\{:[^}]*\})?", r"[[FIG:\1]]", body_md)
    html = markdown.markdown(body_md, extensions=["tables", "sane_lists", "attr_list"])
    if markers:
        (HERE / "P2_REPORT_paste_markers.html").write_text(html)
        print(HERE / "P2_REPORT_paste_markers.html")
        return

    def inline(m):
        src = m.group(1)
        data = base64.b64encode((HERE / src).read_bytes()).decode()
        width = {"fig1_e1_crossing.png": 360, "fig2_e2_core.png": 340}.get(Path(src).name, 620)
        return f'src="data:image/png;base64,{data}" width="{width}"'
    html = re.sub(r'src="(figures/[^"]+\.png)"', inline, html)
    html = re.sub(r' style="max-width:[^"]*"', "", html)
    css = ("body{font:11pt Arial,sans-serif;max-width:720px;margin:20px auto}"
           "table{border-collapse:collapse}th,td{border:1px solid #999;padding:3px 5px;font-size:9pt}")
    (HERE / "P2_REPORT_paste.html").write_text(
        f"<!doctype html><html><head><meta charset='utf-8'><title>paste</title><style>{css}</style></head>"
        f"<body>{html}</body></html>")
    print(HERE / "P2_REPORT_paste.html")


if __name__ == "__main__":
    import sys
    main(markers="--markers" in sys.argv)
