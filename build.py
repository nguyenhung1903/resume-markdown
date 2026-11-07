#!/usr/bin/env python3
import os
import shutil
import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
from string import Template

import markdown

HERE = Path(__file__).resolve().parent
CHECKPOINTS_DIR = HERE / f"resume/checkpoints"

MONTHS = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*"
SEP = " — "  
OWNER_NAME = "An Hung Nguyen"  
DATE_FORMAT = "%B %d, %Y"  # e.g. November 08, 2026

PAGE = Template("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="date" content="$generated_iso">
<title>$title</title>
<style>
$css
</style>
</head>
<body>
<div class="page">
$body
</div>
</body>
</html>
""")


# Markdown -> semantic HTML
def md_to_html(text: str) -> str:
    return markdown.markdown(text, extensions=["extra", "sane_lists"])


def slugify(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


# HTML restructuring (adds the hooks the CSS styles)
def build_entry(chunk: str) -> str:
    """<h3> + following blocks  ->  styled entry with head / meta rows."""
    m = re.match(r"<h3[^>]*>(.*?)</h3>\s*(.*)", chunk, re.S)
    if not m:
        return chunk
    title, rest = m.groups()

    # Optional location line:  <p><em>Danang, VN</em></p>
    location = ""
    lm = re.match(r"<p><em>([^<]*)</em></p>\s*", rest)
    if lm:
        location = lm.group(1)
        rest = rest[lm.end():]

    # Optional meta row:  <p>left - right</p>  (right = date / period)
    meta = ""
    pm = re.match(r"<p>(.*?)</p>\s*", rest, re.S)
    if pm and SEP in pm.group(1):
        left, _, right = pm.group(1).rpartition(SEP)
        meta = (
            '<div class="entry-meta">'
            f'<span class="left">{left}</span><span class="right">{right}</span>'
            "</div>"
        )
        rest = rest[pm.end():]

    loc_html = f'<span class="loc">{location}</span>' if location else ""
    return (
        '<div class="entry">'
        f'<div class="entry-head"><h3>{title}</h3>{loc_html}</div>'
        f"{meta}{rest}</div>"
    )


def build_section(chunk: str) -> str:
    """One <h2>…</h2> block -> <section id=slug> with entries + tweaks."""
    m = re.match(r"<h2[^>]*>(.*?)</h2>\s*(.*)", chunk, re.S)
    if not m:
        return chunk
    heading, rest = m.groups()
    slug = slugify(heading)

    intro, *entries = re.split(r"(?=<h3[ >])", rest)
    body = intro + "".join(build_entry(e) for e in entries)

    # Link bare DOIs:  <li>10.1109/xxx</li>
    body = re.sub(
        r"<li>(10\.\d{4,9}/[^<\s]+)</li>",
        r'<li><a href="https://doi.org/\1">\1</a></li>',
        body,
    )

    # Bold the resume owner's name in author lists
    if slug == "publications":
        body = re.sub(
            rf"(<li>[^<]*?)({re.escape(OWNER_NAME)})",
            r"\1<strong>\2</strong>",
            body,
        )

    # "Mar 2025 - text" -> date column + text column
    if slug == "top-honors-and-awards":
        body = re.sub(
            rf"<li>({MONTHS} \d{{4}}){re.escape(SEP)}(.*?){re.escape(SEP)}(.*?)</li>",
            r'<li><span class="date">\1</span><span>\2</span><span class="right">\3</span></li>',
            body,
        )

    
    # languages
    if slug == "languages":
        body = re.sub(
            r"<li>\s*(.*?):\s*(.*?)\s*</li>",
            lambda m: (
                f'<li><span class="language">{m.group(1)}</span>'
                f'<span>{m.group(2)}</span></li>'
            ),
            body,
        )
    
    return f'<section id="{slug}"><h2>{heading}</h2>{body}</section>'


def structure(html_body: str, generated: str | None = None) -> str:
    # Footer: everything after the last <hr />
    main, sep, footer = html_body.rpartition("<hr />")
    if not sep:
        main, footer = html_body, ""

    header, *sections = re.split(r"(?=<h2[ >])", main)
    out = f'<header class="resume-header">{header}</header>\n'
    out += "\n".join(build_section(s) for s in sections)

    # Footer = original footer text from the Markdown + "Generated on <date>"
    gen_html = f'<p class="generated">{generated}</p>' if generated else ""
    if footer.strip() or gen_html:
        out += f'\n<footer class="resume-footer"><hr />{footer}{gen_html}</footer>'
    return out


def render(md_path: Path, css_path: Path, date_format: str = DATE_FORMAT,
           show_date: bool = True) -> tuple[str, str]:
    now = datetime.now()
    generated = now.strftime(date_format) if show_date else None

    text = md_path.read_text(encoding="utf-8")
    body = structure(md_to_html(text), generated)

    title_m = re.search(r"^#\s+(.+)$", text, re.M)
    title = f"{title_m.group(1).strip()} - Resume" if title_m else "Resume"

    css = css_path.read_text(encoding="utf-8")
    html_str = PAGE.substitute(
        title=title, css=css, body=body, generated_iso=now.strftime("%Y-%m-%d")
    )
    return html_str, title


def write_pdf(html_str: str, pdf_path: Path, base_url: Path) -> bool:
    try:
        from weasyprint import HTML
    except Exception as exc:  # ImportError or missing system libs
        print(f"[!] PDF skipped - WeasyPrint unavailable: {exc}", file=sys.stderr)
        print("    Install with: pip install weasyprint", file=sys.stderr)
        return False
    HTML(string=html_str, base_url=str(base_url)).write_pdf(str(pdf_path))
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description="Markdown CV -> academic resume (HTML + PDF)")
    ap.add_argument("-i", "--input", default=HERE / "resume/CURRENT.md",
                    type=Path, help="Markdown CV file")
    ap.add_argument("-c", "--css", default=HERE / "css/academic_resume.css",
                    type=Path, help="CSS file")
    ap.add_argument("-o", "--out", default= HERE / "dist", type=Path,
                    help="output directory")
    ap.add_argument("-n", "--name", default="resume",
                    help="output base name (default: resume)")
    ap.add_argument("--date-format", default=DATE_FORMAT,
                    help='strftime format for the generated date (default: "%%B %%d, %%Y")')
    ap.add_argument("--no-date", action="store_true",
                    help="do not print the generated date in the footer")
    args = ap.parse_args()

    for p in (args.input, args.css):
        if not p.exists():
            sys.exit(f"File not found: {p}")

    args.out.mkdir(parents=True, exist_ok=True)
    
    
    os.makedirs(CHECKPOINTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy(args.input, os.path.join(CHECKPOINTS_DIR, f"RESUME_{timestamp}.md"))
    
    html_str, _ = render(args.input, args.css, args.date_format, not args.no_date)

    html_path = args.out / f"{args.name}.html"
    html_path.write_text(html_str, encoding="utf-8")
    print(f"HTML -> {html_path}")

    pdf_path = args.out / f"{args.name}.pdf"
    if write_pdf(html_str, pdf_path, args.input.parent):
        print(f"PDF  -> {pdf_path}")


if __name__ == "__main__":
    main()