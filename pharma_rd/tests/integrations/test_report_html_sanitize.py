"""report_html_sanitize (story 7.6)."""

from __future__ import annotations

from pharma_rd.integrations.report_html_sanitize import sanitize_report_html_fragment


def test_sanitize_strips_script_tags() -> None:
    raw = '<p>Safe</p><script>alert("xss")</script><p>After</p>'
    out = sanitize_report_html_fragment(raw)
    assert "<script>" not in out.lower()
    assert "Safe" in out
    assert "After" in out


def test_sanitize_strips_javascript_href() -> None:
    raw = '<p><a href="javascript:alert(1)">click</a></p>'
    out = sanitize_report_html_fragment(raw)
    assert "javascript:" not in out.lower()


def test_sanitize_strips_onclick_handler() -> None:
    raw = '<p onclick="alert(1)">x</p>'
    out = sanitize_report_html_fragment(raw)
    assert "onclick" not in out.lower()


def test_sanitize_strips_iframe() -> None:
    raw = '<iframe src="https://evil.example"></iframe><p>ok</p>'
    out = sanitize_report_html_fragment(raw)
    assert "iframe" not in out.lower()
    assert "ok" in out
