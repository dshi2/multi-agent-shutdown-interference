"""Render P2_REPORT.md to P2_REPORT.pdf: Markdown -> HTML (python-markdown) -> PDF (headless Chrome).

  <python with markdown installed> report/make_pdf.py
"""
import subprocess
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CSS = """
@page { size: A4; margin: 18mm 16mm; }
body { font: 10.5pt/1.45 Georgia, 'Times New Roman', serif; color: #111; max-width: 100%; }
h1 { font-size: 17pt; line-height: 1.25; margin: 0 0 6pt; }
h2 { font-size: 13pt; margin: 16pt 0 4pt; border-bottom: 1px solid #ccc; padding-bottom: 2pt; }
h3 { font-size: 11pt; margin: 12pt 0 3pt; }
p, li { text-align: left; }
table { border-collapse: collapse; font: 8.5pt/1.3 -apple-system, Helvetica, Arial, sans-serif; margin: 6pt 0; width: 100%; }
th, td { border: 1px solid #bbb; padding: 2pt 4pt; vertical-align: top; }
th { background: #f0f0ee; }
img { max-width: 60%; display: block; margin: 8pt auto; }
code { font-size: 9pt; }
"""


def main() -> None:
    md = (HERE / "P2_REPORT.md").read_text()
    body = markdown.markdown(md, extensions=["tables", "sane_lists", "attr_list"])
    html = HERE / "P2_REPORT.html"
    html.write_text(f"<!doctype html><html><head><meta charset='utf-8'><title>P2 report</title>"
                    f"<style>{CSS}</style></head><body>{body}</body></html>")
    pdf = HERE / "P2_REPORT.pdf"
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf}", html.as_uri()], check=True, capture_output=True)
    print(pdf)


if __name__ == "__main__":
    main()
