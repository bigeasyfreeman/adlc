#!/usr/bin/env python3
"""
Convert a markdown file to a styled PDF.

Usage:
    python3 scripts/md2pdf.py <input.md> [output.pdf]

If output path is omitted, writes to the same directory as the input
with a .pdf extension.

Requires: PyMuPDF (pip3 install PyMuPDF)
"""
import sys
import os
import re

try:
    import fitz
except ImportError:
    print("Error: PyMuPDF is required. Install it with:")
    print("  pip3 install PyMuPDF")
    sys.exit(1)


def apply_inline(text):
    """Apply inline markdown formatting to HTML."""
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<b><i>\1</i></b>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    text = re.sub(
        r'`([^`]+)`',
        r'<span style="background-color:#f0f0f0;font-family:monospace;font-size:8px;padding:1px 3px;">\1</span>',
        text,
    )
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    return text


def md_to_html(md_text):
    """Convert markdown to styled HTML suitable for PyMuPDF Story."""
    lines = md_text.split("\n")
    html_parts = []
    in_table = False
    in_code = False

    for line in lines:
        stripped = line.strip()

        # --- Code blocks ---
        if stripped.startswith("```"):
            if in_code:
                html_parts.append("</pre>")
                in_code = False
            else:
                html_parts.append(
                    '<pre style="background-color:#f4f4f4;padding:8px;'
                    "font-size:8px;font-family:monospace;"
                    'border:1px solid #ddd;margin:4px 0;">'
                )
                in_code = True
            continue

        if in_code:
            html_parts.append(line.replace("<", "&lt;").replace(">", "&gt;"))
            continue

        # --- Horizontal rule ---
        if stripped == "---":
            if in_table:
                html_parts.append("</table>")
                in_table = False
            html_parts.append("<hr/>")
            continue

        # --- Empty line ---
        if not stripped:
            html_parts.append("")
            continue

        # --- Table separator row (skip) ---
        if re.match(r"^\|[\s\-:|]+\|$", stripped):
            continue

        # --- Table rows ---
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            if not in_table:
                in_table = True
                html_parts.append(
                    '<table style="width:100%;border-collapse:collapse;'
                    'margin:6px 0;font-size:8px;">'
                )
                html_parts.append("<tr>")
                for cell in cells:
                    html_parts.append(
                        '<th style="border:1px solid #ccc;padding:4px 6px;'
                        'background-color:#f0f0f0;text-align:left;">'
                        f"{apply_inline(cell)}</th>"
                    )
                html_parts.append("</tr>")
            else:
                html_parts.append("<tr>")
                for cell in cells:
                    html_parts.append(
                        '<td style="border:1px solid #ccc;padding:4px 6px;'
                        f'vertical-align:top;">{apply_inline(cell)}</td>'
                    )
                html_parts.append("</tr>")
            continue

        # Close table if no longer in one
        if in_table and not stripped.startswith("|"):
            html_parts.append("</table>")
            in_table = False

        # --- Headers ---
        if stripped.startswith("# "):
            text = apply_inline(stripped[2:])
            html_parts.append(
                f'<h1 style="font-size:18px;color:#1a1a2e;'
                f'margin:16px 0 8px 0;border-bottom:2px solid #6c63ff;">{text}</h1>'
            )
            continue
        if stripped.startswith("## "):
            text = apply_inline(stripped[3:])
            html_parts.append(
                f'<h2 style="font-size:14px;color:#1a1a2e;'
                f'margin:14px 0 6px 0;border-bottom:1px solid #ddd;">{text}</h2>'
            )
            continue
        if stripped.startswith("### "):
            text = apply_inline(stripped[4:])
            html_parts.append(
                f'<h3 style="font-size:11px;color:#333;margin:10px 0 4px 0;">{text}</h3>'
            )
            continue

        # --- List items ---
        if stripped.startswith("- "):
            text = apply_inline(stripped[2:])
            html_parts.append(
                f'<p style="font-size:9px;margin:2px 0 2px 16px;color:#333;">'
                f"&#8226; {text}</p>"
            )
            continue

        # --- Numbered list ---
        m = re.match(r"^(\d+)\.\s+(.+)$", stripped)
        if m:
            text = apply_inline(m.group(2))
            html_parts.append(
                f'<p style="font-size:9px;margin:2px 0 2px 16px;color:#333;">'
                f"{m.group(1)}. {text}</p>"
            )
            continue

        # --- Bold-lead paragraphs (G/W/T) ---
        if stripped.startswith("**GIVEN**") or stripped.startswith("**WHEN**") or stripped.startswith("**THEN**"):
            text = apply_inline(stripped)
            html_parts.append(f'<p style="font-size:9px;margin:2px 0;color:#333;">{text}</p>')
            continue

        # --- Regular paragraph ---
        text = apply_inline(stripped)
        html_parts.append(f'<p style="font-size:9px;margin:3px 0;color:#333;">{text}</p>')

    if in_table:
        html_parts.append("</table>")
    if in_code:
        html_parts.append("</pre>")

    return "\n".join(html_parts)


def convert(input_path, output_path):
    """Convert a markdown file to PDF."""
    with open(input_path, "r", encoding="utf-8") as f:
        md = f.read()

    html_body = md_to_html(md)
    full_html = (
        '<html><body style="font-family:Helvetica,Arial,sans-serif;margin:0;padding:0;">'
        f'<div style="padding:10px;">{html_body}</div>'
        "</body></html>"
    )

    writer = fitz.DocumentWriter(output_path)
    mediabox = fitz.paper_rect("letter")
    where = mediabox + fitz.Rect(50, 50, -50, -50)  # margins

    story = fitz.Story(html=full_html)
    more = True
    while more:
        dev = writer.begin_page(mediabox)
        more, _ = story.place(where)
        story.draw(dev)
        writer.end_page()
    writer.close()

    doc = fitz.open(output_path)
    pages = doc.page_count
    doc.close()

    print(f"Created: {output_path} ({pages} pages)")


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip())
        sys.exit(1)

    input_path = sys.argv[1]
    if not os.path.isfile(input_path):
        print(f"Error: {input_path} not found")
        sys.exit(1)

    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        output_path = os.path.splitext(input_path)[0] + ".pdf"

    convert(input_path, output_path)


if __name__ == "__main__":
    main()
