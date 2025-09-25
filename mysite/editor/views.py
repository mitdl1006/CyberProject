from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST
from markdown_it import MarkdownIt
from weasyprint import HTML

THEME_DEFAULTS: dict[str, Any] = {
    "title": "Untitled",
    "fontFamily": "'Noto Sans KR', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif",
    "baseFontSize": 16,
    "lineHeight": 1.7,
    "textColor": "#1f2933",
    "backgroundColor": "#ffffff",
    "headingColor": "#0f172a",
    "accentColor": "#2563eb",
    "blockquoteBackground": "#eff6ff",
    "blockquoteBorderColor": "#2563eb",
    "blockquoteTextColor": "#1e293b",
    "codeBackground": "#0f172a",
    "codeTextColor": "#facc15",
    "listStyle": "disc",
    "orderedListStyle": "decimal",
    "pagePadding": "48px",
    "cardShadow": "0 30px 60px -30px rgba(37, 99, 235, 0.45)",
}

markdown_engine = MarkdownIt(
    "commonmark", {"linkify": True, "html": True, "typographer": True}
)


def merge_theme(theme: dict[str, Any] | None) -> dict[str, Any]:
    merged = THEME_DEFAULTS.copy()
    if theme:
        for key, value in theme.items():
            if value in (None, ""):
                continue
            merged[key] = value
    return merged


def build_theme_css(theme: dict[str, Any]) -> str:
    base_font_size = theme.get("baseFontSize", 16)
    try:
        font_size_px = int(float(base_font_size))
    except (TypeError, ValueError):
        font_size_px = 16

    line_height = theme.get("lineHeight", 1.7)
    try:
        line_height_value = float(line_height)
    except (TypeError, ValueError):
        line_height_value = 1.7

    page_padding = theme.get("pagePadding", "48px")

    css = f"""
	:root {{
		color-scheme: light;
	}}
	body {{
		margin: 0;
		padding: 0;
		background: {theme["backgroundColor"]};
		color: {theme["textColor"]};
		font-family: {theme["fontFamily"]};
		font-size: {font_size_px}px;
		line-height: {line_height_value};
		-webkit-font-smoothing: antialiased;
	}}
	.document {{
		max-width: 840px;
		margin: 0 auto;
		background: {theme["backgroundColor"]};
		padding: {page_padding};
		box-shadow: {theme["cardShadow"]};
		border-radius: 20px;
		border: 1px solid rgba(15, 23, 42, 0.08);
	}}
	.document h1,
	.document h2,
	.document h3,
	.document h4,
	.document h5,
	.document h6 {{
		color: {theme["headingColor"]};
		font-weight: 700;
		margin-top: 2.2em;
		margin-bottom: 0.8em;
	}}
	.document h1 {{
		font-size: {font_size_px * 2.2}px;
		letter-spacing: -0.03em;
	}}
	.document h2 {{
		font-size: {font_size_px * 1.8}px;
		letter-spacing: -0.025em;
	}}
	.document h3 {{
		font-size: {font_size_px * 1.5}px;
	}}
	.document h4 {{
		font-size: {font_size_px * 1.25}px;
	}}
	.document h5 {{
		font-size: {font_size_px * 1.1}px;
	}}
	.document h6 {{
		font-size: {font_size_px * 1.05}px;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: {theme["accentColor"]};
	}}
	.document a {{
		color: {theme["accentColor"]};
		text-decoration: none;
		border-bottom: 2px solid rgba(37, 99, 235, 0.25);
	}}
	.document a:hover {{
		border-bottom-color: rgba(37, 99, 235, 0.55);
	}}
	.document p {{
		margin: 1.1em 0;
	}}
	.document ul {{
		list-style-type: {theme["listStyle"]};
	}}
	.document ol {{
		list-style-type: {theme["orderedListStyle"]};
	}}
	.document ul,
	.document ol {{
		padding-left: 1.4em;
		margin: 1.2em 0;
	}}
	.document blockquote {{
		margin: 1.6em 0;
		padding: 1.4em 1.6em;
		background: {theme["blockquoteBackground"]};
		border-left: 6px solid {theme["blockquoteBorderColor"]};
		color: {theme["blockquoteTextColor"]};
		border-radius: 0 20px 20px 0;
		box-shadow: inset 0 0 0 1px rgba(15, 23, 42, 0.05);
	}}
	.document code {{
		background: {theme["codeBackground"]};
		color: {theme["codeTextColor"]};
		padding: 0.1em 0.4em;
		border-radius: 6px;
		font-size: {font_size_px * 0.95}px;
	}}
	.document pre code {{
		display: block;
		padding: 1.2em 1.4em;
		border-radius: 16px;
		overflow-x: auto;
	}}
	.document hr {{
		border: none;
		border-top: 1px dashed rgba(15, 23, 42, 0.2);
		margin: 2.5em 0;
	}}
	table {{
		width: 100%;
		border-collapse: collapse;
		margin: 1.6em 0;
		border-radius: 16px;
		overflow: hidden;
		box-shadow: 0 14px 40px -24px rgba(15, 23, 42, 0.25);
	}}
	table thead {{
		background: rgba(37, 99, 235, 0.08);
	}}
	table th,
	table td {{
		border: 1px solid rgba(15, 23, 42, 0.08);
		padding: 1em 1.2em;
		text-align: left;
	}}
	figure {{
		margin: 2em 0;
		text-align: center;
	}}
	figcaption {{
		margin-top: 0.8em;
		font-size: {font_size_px * 0.9}px;
		color: rgba(15, 23, 42, 0.65);
	}}
	.document .badge {{
		display: inline-flex;
		align-items: center;
		gap: 0.4em;
		padding: 0.2em 0.8em;
		background: rgba(37, 99, 235, 0.12);
		border-radius: 999px;
		color: {theme["accentColor"]};
		font-weight: 600;
		letter-spacing: 0.05em;
		text-transform: uppercase;
		font-size: {font_size_px * 0.75}px;
	}}
	"""
    return "\n".join(line.rstrip() for line in css.splitlines())


def render_markdown(markdown_text: str, theme: dict[str, Any]) -> tuple[str, str]:
    html_body = markdown_engine.render(markdown_text or "")
    document_html = f'<div class="document">{html_body}</div>'
    css = build_theme_css(theme)
    return document_html, css


def full_html_document(document_html: str, css: str, title: str) -> str:
    return f"""<!DOCTYPE html>
	<html lang=\"ko\">
	<head>
		<meta charset=\"utf-8\" />
		<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
		<title>{title}</title>
		<style>{css}</style>
	</head>
	<body>
		{document_html}
	</body>
	</html>
	"""


@require_GET
def editor_workspace(request: HttpRequest) -> HttpResponse:
    context = {
        "default_theme": json.dumps(THEME_DEFAULTS, ensure_ascii=False),
    }
    return render(request, "editor/editor.html", context)


def _deserialize_payload(request: HttpRequest) -> tuple[str, dict[str, Any]]:
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError("요청 본문이 JSON 형식이 아닙니다.")

    markdown_text = payload.get("markdown", "")
    theme = merge_theme(payload.get("theme", {}))
    theme["title"] = payload.get("title", theme.get("title", "Untitled"))
    return markdown_text, theme


@require_POST
def live_preview(request: HttpRequest) -> JsonResponse:
    try:
        markdown_text, theme = _deserialize_payload(request)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    document_html, css = render_markdown(markdown_text, theme)
    return JsonResponse(
        {
            "html": document_html,
            "css": css,
        }
    )


@require_POST
def generate_pdf(request: HttpRequest) -> HttpResponse:
    try:
        markdown_text, theme = _deserialize_payload(request)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    document_html, css = render_markdown(markdown_text, theme)
    pdf_html = full_html_document(document_html, css, theme.get("title", "Document"))

    pdf_bytes = HTML(
        string=pdf_html,
        base_url=request.build_absolute_uri("/"),
    ).write_pdf()

    safe_title = theme.get("title") or "Document"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{safe_title}_{timestamp}.pdf".replace(" ", "_")

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
