from __future__ import annotations

import json

from django.test import Client, TestCase
from django.urls import reverse


class EditorViewsTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.sample_payload = {
            "markdown": "# 제목\n\n- 항목 1\n- 항목 2\n\n> 인용문\n\n```python\nprint('hello')\n```",
            "title": "테스트 문서",
            "theme": {
                "baseFontSize": 17,
                "backgroundColor": "#ffffff",
                "textColor": "#111827",
                "headingColor": "#0f172a",
                "accentColor": "#2563eb",
                "listStyle": "disc",
                "orderedListStyle": "decimal",
                "pagePadding": "48px",
                "lineHeight": 1.7,
                "cardShadow": "0 30px 60px -30px rgba(37, 99, 235, 0.45)",
            },
        }

    def test_workspace_page_is_accessible(self) -> None:
        response = self.client.get(reverse("editor:workspace"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Markdown Styler")

    def test_live_preview_returns_html_and_css(self) -> None:
        response = self.client.post(
            reverse("editor:preview"),
            data=json.dumps(self.sample_payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("html", payload)
        self.assertIn("css", payload)
        self.assertIn("document", payload["html"])
        self.assertIn(".document", payload["css"])

    def test_generate_pdf_returns_binary_pdf(self) -> None:
        response = self.client.post(
            reverse("editor:pdf"),
            data=json.dumps(self.sample_payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertGreater(len(response.content), 1000)
