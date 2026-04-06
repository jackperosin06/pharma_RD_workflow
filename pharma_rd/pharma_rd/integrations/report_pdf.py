"""Render HTML insight reports to PDF (WeasyPrint)."""

from __future__ import annotations


def render_pdf_from_html(html: str) -> bytes:
    """Return PDF bytes for a full HTML document string.

    Raises ``RuntimeError`` if WeasyPrint fails or is unavailable.
    """
    try:
        from weasyprint import HTML
    except ImportError as e:
        raise RuntimeError(
            "WeasyPrint is not installed; cannot render PDF."
        ) from e
    try:
        return HTML(string=html).write_pdf()
    except Exception as e:
        raise RuntimeError(f"PDF render failed: {e}") from e
