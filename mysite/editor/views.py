from __future__ import annotations

import json
import textwrap
import unicodedata
from copy import deepcopy
from datetime import datetime
from typing import Any, Sequence

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST
from markdown_it import MarkdownIt
from markdown_it.token import Token
from weasyprint import HTML

markdown_engine = MarkdownIt(
    "commonmark",
    {"html": True, "linkify": True, "typographer": True},
)

THEME_DEFAULTS: dict[str, Any] = {
    "title": "Untitled",
    "fontFamily": "'Noto Sans KR', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif",
    "baseFontSize": 16,
    "backgroundColor": "#ffffff",
    "textColor": "#111827",
    "headingColor": "#0f172a",
    "accentColor": "#2563eb",
    "blockquoteBackground": "#eff6ff",
    "blockquoteBorderColor": "#2563eb",
    "blockquoteTextColor": "#1f2937",
    "blockquoteBorderRadius": "14px",
    "codeBackground": "#0f172a",
    "codeTextColor": "#facc15",
    "listStyle": "disc",
    "orderedListStyle": "decimal",
    "pagePadding": "48px",
    "lineHeight": 1.7,
    "cardShadow": "0 30px 60px -30px rgba(37, 99, 235, 0.45)",
    "orderedMarkerPrefix": "",
    "orderedMarkerSuffix": ".",
    "useCustomBullets": False,
    "customBulletSequence": ["✔️", "❤️", "💡"],
    "useCustomOrdered": False,
    "customOrderedDigits": ["🧐", "●", "A"],
    "customOrderedBase": 3,
}

_COUNTER_STYLES: dict[str, str] = {
    "decimal": "decimal",
    "decimal-leading-zero": "decimal-leading-zero",
    "leading-zero": "decimal-leading-zero",
    "lower-alpha": "lower-alpha",
    "upper-alpha": "upper-alpha",
    "lower-roman": "lower-roman",
    "upper-roman": "upper-roman",
}


def _boolean_value(value: Any, *, default: bool | None = None) -> bool:
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return bool(default) if default is not None else False


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _coerce_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _split_graphemes(text: str) -> list[str]:
    clusters: list[str] = []
    buffer = ""
    for char in text:
        if not buffer:
            buffer = char
            continue
        if (
            unicodedata.combining(char)
            or char == "\u200d"
            or buffer.endswith("\u200d")
            or 0xFE00 <= ord(char) <= 0xFE0F
        ):
            buffer += char
            continue
        clusters.append(buffer)
        buffer = char
    if buffer:
        clusters.append(buffer)
    return clusters


def _normalize_sequence(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if str(item)]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        normalized = text.replace("\r", "\n").replace(",", "\n").replace(";", "\n")
        parts = [part.strip() for part in normalized.split("\n") if part.strip()]
        if not parts:
            return []
        if len(parts) == 1:
            candidate = parts[0]
            if " " in candidate:
                segments = [seg.strip() for seg in candidate.split(" ") if seg.strip()]
            else:
                segments = [candidate]
        else:
            segments = parts
        result: list[str] = []
        for piece in segments:
            clusters = _split_graphemes(piece)
            if len(clusters) <= 1:
                result.append(piece)
            else:
                result.extend(clusters)
        return [item for item in result if item]
    return [str(value)]


def _css_string(value: Any) -> str:
    if value is None:
        return "''"
    escaped = str(value).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


def _counter_style(name: Any) -> str:
    if not name:
        return "decimal"
    key = str(name).strip().lower()
    return _COUNTER_STYLES.get(key, "decimal")


def _number_to_custom_label(index: int, digits: Sequence[str]) -> str:
    if not digits:
        return str(index)
    base = len(digits)
    n = max(1, index)
    result: list[str] = []
    while n > 0:
        n -= 1
        n, remainder = divmod(n, base)
        result.append(digits[remainder])
    return "".join(reversed(result)) or digits[0]


def _apply_custom_lists(tokens: list[Token], theme: dict[str, Any]) -> None:
    use_custom_bullets = _boolean_value(theme.get("useCustomBullets"))
    use_custom_ordered = _boolean_value(theme.get("useCustomOrdered"))
    bullet_sequence = [
        str(item) for item in (theme.get("customBulletSequence") or []) if str(item)
    ]
    ordered_digits = [
        str(item) for item in (theme.get("customOrderedDigits") or []) if str(item)
    ]
    ordered_prefix = str(theme.get("orderedMarkerPrefix") or "")
    ordered_suffix = str(theme.get("orderedMarkerSuffix") or ".")

    stack: list[dict[str, Any]] = []

    for token in tokens:
        if token.type == "bullet_list_open":
            context = {
                "type": "ul",
                "index": 0,
                "sequence": bullet_sequence
                if use_custom_bullets and bullet_sequence
                else None,
            }
            stack.append(context)
        elif token.type == "ordered_list_open":
            start_value = _coerce_int(token.attrGet("start"), 1)
            context = {
                "type": "ol",
                "counter": max(1, start_value),
                "digits": ordered_digits
                if use_custom_ordered and ordered_digits
                else None,
                "prefix": ordered_prefix,
                "suffix": ordered_suffix,
            }
            stack.append(context)
        elif token.type in {"bullet_list_close", "ordered_list_close"}:
            if stack:
                stack.pop()
        elif token.type == "list_item_open" and stack:
            active = stack[-1]
            if active.get("type") == "ul":
                sequence: list[str] | None = active.get("sequence")
                if sequence:
                    index = active.get("index", 0)
                    symbol = sequence[index % len(sequence)]
                    active["index"] = index + 1
                    token.attrSet("data-bullet-symbol", str(symbol))
            elif active.get("type") == "ol":
                digits: list[str] | None = active.get("digits")
                if digits:
                    counter_value = active.get("counter", 1)
                    label = _number_to_custom_label(counter_value, digits)
                    active["counter"] = counter_value + 1
                    token.attrSet(
                        "data-ordered-label",
                        f"{active.get('prefix', '')}{label}{active.get('suffix', '')}",
                    )


def merge_theme(user_theme: dict[str, Any] | None) -> dict[str, Any]:
    theme_input = user_theme or {}
    result = deepcopy(THEME_DEFAULTS)

    for key, value in theme_input.items():
        if key in {"customBulletSequence", "customOrderedDigits"}:
            continue
        if key in {"useCustomBullets", "useCustomOrdered"}:
            result[key] = _boolean_value(value)
        elif key == "baseFontSize":
            result[key] = _coerce_int(value, result[key])
        elif key == "lineHeight":
            result[key] = _coerce_float(value, result[key])
        elif key == "customOrderedBase":
            result[key] = max(2, _coerce_int(value, result[key]))
        elif key == "pagePadding":
            padding = str(value) if value is not None else result[key]
            result[key] = padding if padding.endswith("px") else f"{padding}px"
        elif key == "blockquoteBorderRadius":
            radius = str(value) if value is not None else result[key]
            result[key] = radius if radius.endswith("px") else f"{radius}px"
        else:
            result[key] = value if value is not None else result.get(key)

    if "customBulletSequence" in theme_input:
        result["customBulletSequence"] = _normalize_sequence(
            theme_input.get("customBulletSequence")
        )
    if "customOrderedDigits" in theme_input:
        result["customOrderedDigits"] = _normalize_sequence(
            theme_input.get("customOrderedDigits")
        )

    if not result.get("customBulletSequence"):
        result["useCustomBullets"] = False
    if not result.get("customOrderedDigits"):
        result["useCustomOrdered"] = False

    digits_len = len(result.get("customOrderedDigits") or [])
    if digits_len:
        result["customOrderedBase"] = digits_len
    else:
        result["customOrderedBase"] = max(
            2, _coerce_int(result.get("customOrderedBase"), 10)
        )

    return result


def build_theme_css(theme: dict[str, Any]) -> str:
    font_size_px = _coerce_int(theme.get("baseFontSize"), 16)
    line_height = _coerce_float(theme.get("lineHeight"), 1.7)
    page_padding = str(theme.get("pagePadding") or "48px")
    list_style = str(theme.get("listStyle") or "disc")
    ordered_style = _counter_style(theme.get("orderedListStyle"))
    use_custom_bullets = _boolean_value(theme.get("useCustomBullets")) and bool(
        theme.get("customBulletSequence")
    )
    use_custom_ordered = _boolean_value(theme.get("useCustomOrdered")) and bool(
        theme.get("customOrderedDigits")
    )

    base_css = textwrap.dedent(
        f"""
        :root {{
            color-scheme: light;
        }}
        body {{
            margin: 0;
            padding: 0;
            background: {theme["backgroundColor"]};
            color: {theme["textColor"]};
            font-family: 'Noto Sans KR', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
            font-size: {font_size_px}px;
            line-height: {line_height};
            -webkit-font-smoothing: antialiased;
        }}
        .document {{
            width: 100%;
            margin: 0;
            background: {theme["backgroundColor"]};
            padding: {page_padding};
            box-shadow: {theme["cardShadow"]};
            border-radius: 20px;
            border: 1px solid rgba(15, 23, 42, 0.08);
            font-family: {theme["fontFamily"]};
            box-sizing: border-box;
        }}
        .document h1,
        .document h2,
        .document h3,
        .document h4,
        .document h5 {{
            color: {theme["headingColor"]};
            margin-top: 1.6em;
            margin-bottom: 0.6em;
            font-weight: 700;
        }}
        .document h1 {{ font-size: 1.9em; }}
        .document h2 {{ font-size: 1.6em; }}
        .document h3 {{ font-size: 1.35em; }}
        .document p {{
            margin: 0.75em 0;
        }}
        .document a {{
            color: {theme["accentColor"]};
            text-decoration: none;
        }}
        .document a:hover {{
            text-decoration: underline;
        }}
        .document ul {{
            list-style: {list_style};
            padding-left: 1.55em;
            margin: 0.6em 0;
        }}
        .document ol {{
            list-style: {ordered_style};
            padding-left: 1.85em;
            margin: 0.6em 0;
        }}
        .document li {{
            margin: 0.35em 0;
        }}
        .document blockquote {{
            margin: 1.4em 0;
            padding: 1.1em 1.4em;
            background: {theme["blockquoteBackground"]};
            border-left: 4px solid {theme["blockquoteBorderColor"]};
            color: {theme["blockquoteTextColor"]};
            border-radius: {theme["blockquoteBorderRadius"]};
        }}
        .document code {{
            background: {theme["codeBackground"]};
            color: {theme["codeTextColor"]};
            padding: 0.2em 0.45em;
            border-radius: 8px;
            font-family: 'Fira Code', 'Cascadia Code', Consolas, monospace;
            font-size: 0.92em;
        }}
        .document pre code {{
            display: block;
            padding: 1.2em 1.4em;
            overflow-x: auto;
            border-radius: 16px;
        }}
        .document table {{
            border-collapse: collapse;
            width: 100%;
            margin: 1.5em 0;
        }}
        .document th,
        .document td {{
            border: 1px solid rgba(15, 23, 42, 0.12);
            padding: 0.6em 0.8em;
            text-align: left;
        }}
        .document hr {{
            border: none;
            border-top: 1px solid rgba(15, 23, 42, 0.12);
            margin: 2em 0;
        }}
        .document strong {{
            font-weight: 700;
        }}
        """
    )

    css_parts = [base_css]

    if use_custom_bullets:
        css_parts.append(
            textwrap.dedent(
                f"""
                .document--custom-bullets ul {{
                    list-style: none;
                    margin: 0.6em 0;
                    padding-left: 0;
                }}
                .document--custom-bullets ul ul {{
                    margin-left: 1.6em;
                }}
                .document--custom-bullets li[data-bullet-symbol] {{
                    position: relative;
                    padding-left: 1.9em;
                }}
                .document--custom-bullets li[data-bullet-symbol]::before {{
                    content: attr(data-bullet-symbol);
                    position: absolute;
                    left: 0;
                    top: 0.1em;
                    font-weight: 600;
                    color: {theme["accentColor"]};
                    font-family: {theme["fontFamily"]};
                    font-size: 1em;
                    line-height: 1.2;
                }}
                """
            )
        )

    if use_custom_ordered:
        css_parts.append(
            textwrap.dedent(
                f"""
                .document--custom-ordered ol {{
                    list-style: none;
                    margin: 0.6em 0;
                    padding-left: 0;
                }}
                .document--custom-ordered ol ol {{
                    margin-left: 2em;
                }}
                .document--custom-ordered li[data-ordered-label] {{
                    position: relative;
                    padding-left: 2.6em;
                }}
                .document--custom-ordered li[data-ordered-label]::before {{
                    content: attr(data-ordered-label);
                    position: absolute;
                    left: 0;
                    top: 0.05em;
                    font-weight: 700;
                    color: {theme["accentColor"]};
                    font-family: {theme["fontFamily"]};
                    font-size: 1em;
                    line-height: 1.2;
                    min-width: 2em;
                    text-align: right;
                    display: inline-block;
                }}
                """
            )
        )

    css = "\n".join(css_parts)
    return "\n".join(line.rstrip() for line in css.splitlines())


def render_markdown(markdown_text: str, theme: dict[str, Any]) -> tuple[str, str]:
    tokens = markdown_engine.parse(markdown_text or "")
    use_custom_bullets = _boolean_value(theme.get("useCustomBullets")) and bool(
        theme.get("customBulletSequence")
    )
    use_custom_ordered = _boolean_value(theme.get("useCustomOrdered")) and bool(
        theme.get("customOrderedDigits")
    )

    if use_custom_bullets or use_custom_ordered:
        _apply_custom_lists(tokens, theme)

    html_body = markdown_engine.renderer.render(tokens, markdown_engine.options, {})
    document_classes = ["document"]
    if use_custom_bullets:
        document_classes.append("document--custom-bullets")
    if use_custom_ordered:
        document_classes.append("document--custom-ordered")

    class_attr = " ".join(document_classes)
    document_html = f'<div class="{class_attr}">{html_body}</div>'
    css = build_theme_css(theme)
    return document_html, css


def full_html_document(document_html: str, css: str, title: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
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
    except (
        json.JSONDecodeError,
        UnicodeDecodeError,
    ) as exc:  # pragma: no cover - handled upstream
        raise ValueError("요청 본문이 JSON 형식이 아닙니다.") from exc

    markdown_text = payload.get("markdown", "")
    theme = merge_theme(payload.get("theme", {}))
    theme["title"] = payload.get("title", theme.get("title", "Untitled"))
    return markdown_text, theme


def _json_error(message: str, *, status: int = 400) -> JsonResponse:
    return JsonResponse({"error": message}, status=status)


@require_POST
def live_preview(request: HttpRequest) -> JsonResponse:
    try:
        markdown_text, theme = _deserialize_payload(request)
    except ValueError as exc:
        return _json_error(str(exc))

    document_html, css = render_markdown(markdown_text, theme)
    return JsonResponse(
        {
            "html": document_html,
            "css": css,
            "title": theme.get("title", "Untitled"),
        }
    )


@require_POST
def generate_pdf(request: HttpRequest) -> HttpResponse:
    try:
        markdown_text, theme = _deserialize_payload(request)
    except ValueError as exc:
        return _json_error(str(exc))

    document_html, css = render_markdown(markdown_text, theme)
    html_document = full_html_document(
        document_html, css, theme.get("title", "Untitled")
    )
    base_url = request.build_absolute_uri("/")
    pdf_bytes = HTML(string=html_document, base_url=base_url).write_pdf()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{theme.get('title', 'Document')}_{timestamp}.pdf"

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
