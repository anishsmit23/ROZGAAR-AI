from __future__ import annotations

from html import escape

from markdown import markdown
from weasyprint import CSS, HTML


def markdown_to_pdf(md_text: str, applicant_name: str = "") -> bytes:
    """Render Markdown resume content into print-ready PDF bytes."""
    body_html = markdown(
        md_text or "",
        extensions=["extra", "fenced_code", "sane_lists", "tables"],
        output_format="html5",
    )

    safe_name = escape(applicant_name.strip()) if applicant_name.strip() else ""
    name_block = f"<h1 class=\"applicant-name\">{safe_name}</h1>" if safe_name else ""

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Resume</title>
</head>
<body>
  <article class="resume-page">
    <header class="resume-header">
      {name_block}
    </header>
    <section class="resume-content">
      {body_html}
    </section>
  </article>
</body>
</html>"""

    css = """
        @page {
            size: A4;
            margin: 0.7in;
        }

        html, body {
            margin: 0;
            padding: 0;
            background: #ffffff;
            color: #000000;
            font-family: Arial, Helvetica, sans-serif;
            font-size: 11pt;
            line-height: 1.45;
        }

        .resume-page {
            width: 100%;
        }

        .resume-header {
            margin-bottom: 18px;
            padding-bottom: 10px;
            border-bottom: 1px solid #000000;
        }

        .applicant-name {
            margin: 0;
            font-size: 22pt;
            font-weight: 700;
            letter-spacing: 0.2px;
        }

        .resume-content h1,
        .resume-content h2,
        .resume-content h3,
        .resume-content h4 {
            margin: 18px 0 8px;
            padding-bottom: 6px;
            font-size: 12.5pt;
            font-weight: 700;
            border-bottom: 1px solid #000000;
        }

        .resume-content p {
            margin: 0 0 10px;
        }

        .resume-content ul,
        .resume-content ol {
            margin: 0 0 12px 20px;
            padding: 0;
        }

        .resume-content li {
            margin: 0 0 5px;
        }

        .resume-content a {
            color: #000000;
            text-decoration: none;
        }

        .resume-content strong {
            font-weight: 700;
        }

        .resume-content code,
        .resume-content pre {
            font-family: Consolas, "Courier New", monospace;
            font-size: 10pt;
            white-space: pre-wrap;
        }

        .resume-content blockquote {
            margin: 0 0 12px;
            padding-left: 12px;
            border-left: 2px solid #000000;
        }
    """

    return HTML(string=html).write_pdf(stylesheets=[CSS(string=css)])
