"""Render docs/MANUAL_zh.md to docs/MANUAL_zh.pdf using weasyprint.

Why this exists:
  - The audience is non-technical Chinese-speaking friends.
  - GitHub-rendered markdown is fine but not shareable via WeChat /
    iMessage as a single file.
  - This script bundles the markdown + a print-friendly CSS into a
    single self-contained PDF with proper CJK font rendering.

Run:  python3 docs/build_pdf.py
Output: docs/MANUAL_zh.pdf
"""
from __future__ import annotations

import os
import re
import sys

try:
    import markdown  # markdown-it-py would be nicer but markdown is in pip default
except ImportError:
    print("Installing markdown...")
    os.system(f"{sys.executable} -m pip install --quiet markdown")
    import markdown  # noqa: E402

from weasyprint import HTML, CSS  # noqa: E402


HERE = os.path.dirname(os.path.abspath(__file__))
MD_PATH = os.path.join(HERE, "MANUAL_zh.md")
PDF_PATH = os.path.join(HERE, "MANUAL_zh.pdf")


CSS_BODY = r"""
@page {
    size: A4;
    margin: 18mm 16mm 18mm 16mm;
    @bottom-center {
        content: counter(page) " / " counter(pages);
        font-family: "WenQuanYi Zen Hei", "PingFang SC", "Microsoft YaHei", sans-serif;
        font-size: 9pt;
        color: #888;
    }
}

html {
    font-size: 11pt;
}

body {
    font-family: "WenQuanYi Zen Hei", "PingFang SC", "Microsoft YaHei",
                 "Source Han Sans CN", "Hiragino Sans GB", sans-serif;
    line-height: 1.65;
    color: #1f2328;
    max-width: 180mm;
    margin: 0 auto;
}

h1 {
    font-size: 22pt;
    color: #0969da;
    border-bottom: 2pt solid #0969da;
    padding-bottom: 6pt;
    margin: 0 0 14pt 0;
    page-break-before: always;
}
h1:first-of-type { page-break-before: avoid; }

h2 {
    font-size: 16pt;
    color: #1f883d;
    margin: 22pt 0 8pt 0;
    border-left: 4pt solid #1f883d;
    padding-left: 10pt;
}
h3 {
    font-size: 13pt;
    color: #1f2328;
    margin: 16pt 0 6pt 0;
}
h4 {
    font-size: 11pt;
    color: #6e7681;
    margin: 12pt 0 4pt 0;
    text-transform: uppercase;
    letter-spacing: 0.5pt;
}

p {
    margin: 6pt 0;
    text-align: justify;
}

ul, ol {
    margin: 6pt 0 6pt 0;
    padding-left: 22pt;
}
li { margin: 3pt 0; }

table {
    width: 100%;
    border-collapse: collapse;
    margin: 8pt 0;
    font-size: 10pt;
    page-break-inside: avoid;
}
th, td {
    border: 0.5pt solid #d0d7de;
    padding: 5pt 8pt;
    text-align: left;
    vertical-align: top;
}
th {
    background: #f6f8fa;
    font-weight: 600;
}
tr:nth-child(even) td { background: #fafbfc; }

code {
    font-family: "Menlo", "Consolas", "Courier New", monospace;
    font-size: 9.5pt;
    background: #f6f8fa;
    padding: 1pt 4pt;
    border-radius: 3pt;
    color: #cf222e;
}

pre {
    background: #1f2328;
    color: #f6f8fa;
    padding: 8pt 12pt;
    border-radius: 4pt;
    font-family: "Menlo", "Consolas", "Courier New", monospace;
    font-size: 9pt;
    line-height: 1.5;
    overflow-x: auto;
    page-break-inside: avoid;
    margin: 8pt 0;
}
pre code {
    background: transparent;
    color: inherit;
    padding: 0;
}

blockquote {
    border-left: 3pt solid #d0d7de;
    margin: 8pt 0;
    padding: 4pt 14pt;
    color: #6e7681;
    background: #fafbfc;
    font-style: italic;
}

hr {
    border: none;
    border-top: 0.5pt solid #d0d7de;
    margin: 16pt 0;
}

strong { font-weight: 700; color: #1f2328; }
em { color: #1f883d; }

a { color: #0969da; text-decoration: none; }

/* Emoji + special markers */
.emoji { font-size: 1.1em; }

/* Make the front matter title page distinctive */
h1:first-of-type {
    font-size: 28pt;
    color: #0969da;
    text-align: center;
    margin-top: 20mm;
    margin-bottom: 4mm;
    border-bottom: none;
}
h1:first-of-type + blockquote {
    text-align: center;
    background: transparent;
    border-left: none;
    color: #6e7681;
    font-size: 11pt;
}
"""


def render() -> None:
    with open(MD_PATH, "r", encoding="utf-8") as f:
        md_text = f.read()

    html_body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "sane_lists", "nl2br"],
    )

    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<title>Polymarket 套利助手 · 使用手册</title>
</head>
<body>
{html_body}
</body>
</html>"""

    print(f"Rendering markdown ({len(md_text):,} chars) -> PDF...")
    HTML(string=full_html, base_url=HERE).write_pdf(
        PDF_PATH,
        stylesheets=[CSS(string=CSS_BODY)],
    )
    size = os.path.getsize(PDF_PATH)
    print(f"  wrote {PDF_PATH}  ({size / 1024:.1f} KB)")


if __name__ == "__main__":
    render()
