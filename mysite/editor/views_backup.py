from __future__ import annotations

import json
def render_markdown(markdown_text: str, theme: dict[str, Any]) -> tuple[str, str]:
	html_body = markdown_engine.render(markdown_text or "")
	document_classes = ["document"]
	if _boolean_value(theme.get("useCustomBullets")):
		document_classes.append("document--custom-bullets")
	if _boolean_value(theme.get("useCustomOrdered")):
		document_classes.append("document--custom-ordered")
	class_attr = " ".join(document_classes)
	document_html = f'<div class="{class_attr}">{html_body}</div>'
	css = build_theme_css(theme)
	return document_html, css
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

	use_custom_bullets = _boolean_value(theme.get("useCustomBullets"))
	use_custom_ordered = _boolean_value(theme.get("useCustomOrdered"))

	css = textwrap.dedent(
		f"""
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
.document--custom-bullets ul > li::before {
	position: absolute;
	left: 0;
	top: 0.2em;
}
"""
		custom_symbols = [
			theme.get("customBulletLevel1", ""),
			theme.get("customBulletLevel2", ""),
			theme.get("customBulletLevel3", ""),
			theme.get("customBulletLevel4", ""),
			theme.get("customBulletLevel5", ""),
		]
		for depth, symbol in enumerate(custom_symbols):
			if not symbol:
				continue
			nested = ".document--custom-bullets " + " ".join(["ul"] * (depth + 1))
			css += (
				f"{nested} > li::before {{\n"
				f"    content: {_css_string(symbol)};\n"
				"}\n"
			)

	if use_custom_ordered:
		prefix = theme.get("orderedMarkerPrefix", "")
		suffix = theme.get("orderedMarkerSuffix", ".")
		counter_style = _counter_style(theme.get("orderedListStyle"))
		css += f"""
.document--custom-ordered ol {{
	list-style: none;
	margin: 1.2em 0;
	padding-left: 0;
	counter-reset: document-ordered;
}}
.document--custom-ordered ol > li {{
	position: relative;
	padding-left: 2.6em;
	margin: 0.6em 0;
	counter-increment: document-ordered;
}}
.document--custom-ordered ol > li::before {{
	content: {_css_string(prefix)} counter(document-ordered, {counter_style}) {_css_string(suffix)};
	position: absolute;
	left: 0;
	top: 0.1em;
	font-weight: 700;
	color: {theme["accentColor"]};
}}
.document--custom-ordered ol ol {{
	counter-reset: document-ordered;
}}
"""

	return "\n".join(line.rstrip() for line in css.splitlines())


def render_markdown(markdown_text: str, theme: dict[str, Any]) -> tuple[str, str]:
	html_body = markdown_engine.render(markdown_text or "")
	document_classes = ["document"]
	if _boolean_value(theme.get("useCustomBullets")):
		document_classes.append("document--custom-bullets")
	if _boolean_value(theme.get("useCustomOrdered")):
		document_classes.append("document--custom-ordered")
	class_attr = " ".join(document_classes)
	document_html = f'<div class="{class_attr}">{html_body}</div>'
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
