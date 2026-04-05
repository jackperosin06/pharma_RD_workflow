"""Sanitize GPT-produced HTML before writing report.html (story 7.6 / NFR-S1)."""

from __future__ import annotations

import nh3

# Explicit URL schemes for <a href>; blocks javascript:, data:, etc. Tag allowlist
# follows nh3 defaults unless we pass ``tags=`` (see nh3 docs / ammonia parity).
_DEFAULT_URL_SCHEMES = frozenset({"http", "https", "mailto"})


def sanitize_report_html_fragment(fragment: str) -> str:
    """Allowlist-based sanitization via **nh3** (Rust ammonia bindings).

    Strips ``script``, event handlers, and disallowed tags. Safe for local
    ``file://`` viewing when combined with a trusted document shell in
    ``delivery.py``. ``url_schemes`` is set explicitly so ``javascript:`` and
    other active schemes are not preserved across nh3 versions.
    """
    return nh3.clean(
        fragment.strip() or "<p></p>",
        url_schemes=_DEFAULT_URL_SCHEMES,
    )
