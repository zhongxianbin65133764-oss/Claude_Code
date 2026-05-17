"""Render the magazine deck (index.html) to a print-friendly PDF.

The deck was built with the guizang-ppt-skill template — JavaScript
drives horizontal swipe, WebGL backgrounds, and Motion-One entry
animations. None of that survives a PDF export, so this script
applies an extra print-stylesheet that:

  - Stacks all slides vertically (one per page)
  - Hides the WebGL canvases, nav dots, hints
  - Makes hero overlays opaque so backgrounds aren't washed out
  - Forces opacity:1 on [data-anim] so content is visible
  - Page size set to 16:9 (297 × 167 mm) for presentation feel

Run:  python3 docs/manual_deck/build_pdf.py
Out:  docs/manual_deck/Polymarket_Manual_Deck.pdf
"""
from __future__ import annotations

import os
from weasyprint import HTML, CSS

HERE = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = os.path.join(HERE, "index.html")
PDF_PATH = os.path.join(HERE, "Polymarket_Manual_Deck.pdf")


# 16:9 landscape, no margin so each slide fills the page.
# IMPORTANT: weasyprint maps vw/vh to a default ~794px viewport, not the
# @page size, so the deck's vw-based typography comes out tiny.
# We override every type-sized class with explicit mm/pt values tuned for
# the 297×167mm page area.
PRINT_CSS = r"""
@page {
    size: 297mm 167mm;
    margin: 0;
}

@media print {
    html, body {
        background: var(--paper) !important;
        overflow: visible !important;
        height: auto !important;
        width: auto !important;
    }

    canvas.bg, #nav, #hint { display: none !important; }

    #deck {
        position: static !important;
        width: 100% !important;
        height: auto !important;
        display: block !important;
        flex-wrap: nowrap !important;
        transform: none !important;
        transition: none !important;
        inset: auto !important;
    }

    .slide {
        position: relative !important;
        width: 297mm !important;
        height: 167mm !important;
        max-height: 167mm !important;
        flex: 0 0 auto !important;
        padding: 10mm 14mm 12mm 14mm !important;
        overflow: hidden !important;
        page-break-after: always !important;
        page-break-inside: avoid !important;
    }
    .slide:last-of-type {
        page-break-after: auto !important;
    }
    /* Slide 5 (A vs B) and 15 are the densest two-column layouts.
       Shrink their bullet list to ensure the foot fits on the page. */
    .slide.dark .grid-2-6-6 ul,
    .slide.light .grid-2-6-6 ul {
        font-size: 10pt !important;
        line-height: 1.5 !important;
    }
    .slide.dark .grid-2-6-6 .h-md,
    .slide.light .grid-2-6-6 .h-md {
        font-size: 14pt !important;
    }

    /* Solid backgrounds (no WebGL in print). */
    .slide.light, .slide.hero.light {
        background: var(--paper) !important;
        color: var(--ink) !important;
    }
    .slide.dark, .slide.hero.dark {
        background: var(--ink) !important;
        color: var(--paper) !important;
    }
    .slide::before, .slide::after { display: none !important; }

    /* Reveal all data-anim content (no JS). */
    [data-anim],
    [data-animate="pipeline"] [data-anim] {
        opacity: 1 !important;
        transform: none !important;
    }

    /* ============ Explicit typography in mm/pt ============
       The deck uses vw/vh which weasyprint underestimates.
       Below: equivalents at the 297×167mm page area. */

    /* Magazine chrome */
    .chrome, .foot { font-size: 10pt !important; letter-spacing: .18em !important; }
    .kicker { font-size: 9pt !important; letter-spacing: .28em !important; margin-bottom: 6mm !important; }
    .meta-row { font-size: 9pt !important; letter-spacing: .16em !important; }

    /* Big headings */
    .h-hero { font-size: 72pt !important; line-height: 1.02 !important; }
    .h-xl   { font-size: 44pt !important; line-height: 1.08 !important; }
    .h-sub  { font-size: 26pt !important; line-height: 1.22 !important; }
    .h-md   { font-size: 18pt !important; line-height: 1.28 !important; }

    /* Lead / body */
    .lead       { font-size: 15pt !important; line-height: 1.42 !important; }
    .body-zh    { font-size: 12pt !important; line-height: 1.7 !important; }

    /* Big quote slides: override the inline vw font-sizes */
    blockquote { font-size: 42pt !important; line-height: 1.2 !important; }
    blockquote span[data-anim="line"] { font-size: 42pt !important; }

    /* Stat numbers (data-cards) */
    .stat-card .stat-label { font-size: 9pt !important; letter-spacing: .22em !important; }
    .stat-card .stat-nb    { font-size: 46pt !important; line-height: 0.95 !important; }
    .grid-3 .stat-card .stat-nb { font-size: 54pt !important; }
    .grid-4 .stat-card .stat-nb { font-size: 42pt !important; }
    .stat-card .stat-nb .stat-unit { font-size: 18pt !important; }
    .stat-card .stat-note  { font-size: 11pt !important; line-height: 1.45 !important; }

    /* The hero +$5.20 number on slide 10 (.big-num inline 14vw) */
    .big-num { font-size: 96pt !important; line-height: 0.95 !important; }

    /* Pipeline steps */
    .pipeline-label { font-size: 9pt !important; letter-spacing: .26em !important; }
    .step-nb    { font-size: 13pt !important; }
    .step-title { font-size: 16pt !important; line-height: 1.18 !important; }
    .step-desc  { font-size: 10pt !important; line-height: 1.42 !important; }

    /* Rowline (FAQ + cheatsheet) */
    .rowline .k { font-size: 16pt !important; line-height: 1.2 !important; }
    .rowline .v { font-size: 12pt !important; line-height: 1.55 !important; }
    .rowline .m { font-size: 9pt !important; letter-spacing: .2em !important; }

    /* Callout */
    .callout { font-size: 13pt !important; line-height: 1.55 !important; padding: 8mm 6mm !important; }
    .callout-src { font-size: 9pt !important; letter-spacing: .2em !important; margin-top: 5mm !important; }

    /* Blockquote inline-styled sizes — keep them dramatic but legible */
    blockquote span[data-anim="line"] { font-size: inherit !important; }

    /* Image caption */
    .img-cap { font-size: 9pt !important; letter-spacing: .22em !important; }
}
"""


def render() -> None:
    if not os.path.exists(HTML_PATH):
        raise SystemExit(f"index.html not found at {HTML_PATH}")

    print(f"Rendering deck -> PDF...")
    print(f"  source: {HTML_PATH}")
    HTML(filename=HTML_PATH, base_url=HERE).write_pdf(
        PDF_PATH,
        stylesheets=[CSS(string=PRINT_CSS)],
    )
    size_kb = os.path.getsize(PDF_PATH) / 1024
    print(f"  output: {PDF_PATH}  ({size_kb:.1f} KB)")


if __name__ == "__main__":
    render()
