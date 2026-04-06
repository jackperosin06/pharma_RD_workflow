"""FR19 insight report distribution (file drop MVP)."""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Literal

from pharma_rd.config import Settings

# Local return types only — avoid importing pipeline.contracts here (circular import via
# pipeline package __init__ → delivery → this module).

_DETAIL_MAX = 500

_DistCh = Literal["none", "file_drop", "smtp"]
_DistSt = Literal["ok", "failed", "skipped"]


def _clip(s: str, max_len: int = _DETAIL_MAX) -> str:
    t = s.strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _run_id_is_safe(run_id: str) -> bool:
    """Reject path segments that could escape ``artifact_root`` / drop-dir subtrees."""
    if not run_id or run_id != run_id.strip():
        return False
    p = Path(run_id)
    if len(p.parts) != 1:
        return False
    if p.parts[0] in (".", ".."):
        return False
    return True


def distribute_insight_report(
    run_id: str,
    artifact_root: Path,
    *,
    settings: Settings,
    logger: logging.Logger,
) -> tuple[_DistCh, _DistSt, str]:
    """Copy ``report.md`` (and ``report.html`` when present) to R&D and marketing.

    Or record skip/failure.
    """
    ch = settings.distribution_channel

    if ch == "none":
        logger.info(
            "distribution skipped",
            extra={
                "event": "distribution_skipped",
                "outcome": "skipped",
                "distribution_channel": "none",
                "distribution_status": "skipped",
                "distribution_detail": (
                    "PHARMA_RD_DISTRIBUTION_CHANNEL=none (explicit no-op)"
                ),
            },
        )
        return "none", "skipped", (
            "distribution disabled (PHARMA_RD_DISTRIBUTION_CHANNEL=none)"
        )

    if ch == "smtp":
        logger.error(
            "distribution failed",
            extra={
                "event": "distribution_failed",
                "outcome": "failed",
                "error_type": "smtp_not_implemented",
                "distribution_channel": "smtp",
                "distribution_status": "failed",
                "distribution_detail": (
                    "SMTP not implemented in MVP; use file_drop or none"
                ),
            },
        )
        return "smtp", "failed", (
            "SMTP not implemented in MVP; use file_drop or none"
        )

    # file_drop
    if not settings.distribution_drop_dir:
        detail = (
            "PHARMA_RD_DISTRIBUTION_DROP_DIR required when "
            "distribution_channel=file_drop"
        )
        logger.error(
            "distribution failed",
            extra={
                "event": "distribution_failed",
                "outcome": "failed",
                "error_type": "missing_drop_dir",
                "distribution_channel": "file_drop",
                "distribution_status": "failed",
                "distribution_detail": detail,
            },
        )
        return "file_drop", "failed", detail

    if not _run_id_is_safe(run_id):
        detail = "run_id must be a single safe segment (no path separators or ..)"
        logger.error(
            "distribution failed",
            extra={
                "event": "distribution_failed",
                "outcome": "failed",
                "error_type": "invalid_run_id",
                "distribution_channel": "file_drop",
                "distribution_status": "failed",
                "distribution_detail": detail,
            },
        )
        return "file_drop", "failed", detail

    report = artifact_root / run_id / "delivery" / "report.md"
    if not report.is_file():
        detail = f"Missing report artifact: {report}"
        logger.error(
            "distribution failed",
            extra={
                "event": "distribution_failed",
                "outcome": "failed",
                "error_type": "missing_report",
                "distribution_channel": "file_drop",
                "distribution_status": "failed",
                "distribution_detail": _clip(detail, 300),
            },
        )
        return "file_drop", "failed", _clip(detail)

    try:
        base = Path(settings.distribution_drop_dir).expanduser().resolve()
        base.mkdir(parents=True, exist_ok=True)
        rd_dst = base / "rd" / run_id
        mkt_dst = base / "marketing" / run_id
        rd_dst.mkdir(parents=True, exist_ok=True)
        mkt_dst.mkdir(parents=True, exist_ok=True)
        rd_file = rd_dst / "report.md"
        mkt_file = mkt_dst / "report.md"
        shutil.copy2(report, rd_file)
        shutil.copy2(report, mkt_file)
        html_src = artifact_root / run_id / "delivery" / "report.html"
        manifest: dict[str, object] = {
            "run_id": run_id,
            "rd_report_path": str(rd_file.resolve()),
            "marketing_report_path": str(mkt_file.resolve()),
            "source_artifact_relative": f"{run_id}/delivery/report.md",
        }
        if html_src.is_file():
            rd_html = rd_dst / "report.html"
            mkt_html = mkt_dst / "report.html"
            shutil.copy2(html_src, rd_html)
            shutil.copy2(html_src, mkt_html)
            manifest["rd_report_html_path"] = str(rd_html.resolve())
            manifest["marketing_report_html_path"] = str(mkt_html.resolve())
            manifest["source_artifact_html_relative"] = f"{run_id}/delivery/report.html"
        docx_src = artifact_root / run_id / "delivery" / "report.docx"
        if docx_src.is_file():
            rd_docx = rd_dst / "report.docx"
            mkt_docx = mkt_dst / "report.docx"
            shutil.copy2(docx_src, rd_docx)
            shutil.copy2(docx_src, mkt_docx)
            manifest["rd_report_docx_path"] = str(rd_docx.resolve())
            manifest["marketing_report_docx_path"] = str(mkt_docx.resolve())
            manifest["source_artifact_docx_relative"] = (
                f"{run_id}/delivery/report.docx"
            )
        pdf_src = artifact_root / run_id / "delivery" / "report.pdf"
        if pdf_src.is_file():
            rd_pdf = rd_dst / "report.pdf"
            mkt_pdf = mkt_dst / "report.pdf"
            shutil.copy2(pdf_src, rd_pdf)
            shutil.copy2(pdf_src, mkt_pdf)
            manifest["rd_report_pdf_path"] = str(rd_pdf.resolve())
            manifest["marketing_report_pdf_path"] = str(mkt_pdf.resolve())
            manifest["source_artifact_pdf_relative"] = f"{run_id}/delivery/report.pdf"
        manifest_dir = base / run_id
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = manifest_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as e:
        detail = f"filesystem error: {e}"
        logger.error(
            "distribution failed",
            extra={
                "event": "distribution_failed",
                "outcome": "failed",
                "error_type": "filesystem",
                "distribution_channel": "file_drop",
                "distribution_status": "failed",
                "distribution_detail": _clip(detail, 300),
            },
        )
        return "file_drop", "failed", _clip(detail)

    ok_detail = f"manifest={manifest_path.resolve()}"
    logger.info(
        "distribution complete",
        extra={
            "event": "distribution_complete",
            "outcome": "ok",
            "distribution_channel": "file_drop",
            "distribution_status": "ok",
            "distribution_detail": _clip(ok_detail, 300),
        },
    )
    return "file_drop", "ok", _clip(ok_detail)
