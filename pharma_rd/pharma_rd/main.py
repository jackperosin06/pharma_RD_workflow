"""CLI entrypoint — `pharma-rd` (run, runs, status, scheduler)."""

from __future__ import annotations

import argparse
import sys

from pydantic import ValidationError

from pharma_rd import __version__


def _positive_int(name: str):
    def _parse(s: str) -> int:
        try:
            n = int(s)
        except ValueError as e:
            raise argparse.ArgumentTypeError(f"{name} must be an integer") from e
        if n < 1:
            raise argparse.ArgumentTypeError(f"{name} must be at least 1")
        return n

    return _parse


def main_exit_code() -> int:
    parser = argparse.ArgumentParser(
        prog="pharma-rd",
        description="Pharma R&D multi-agent pipeline (Epic 1–2).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    sub.add_parser(
        "run",
        help="Create a run and execute the full pipeline on demand (FR1).",
    )

    p_runs = sub.add_parser(
        "runs",
        help="List recent runs from SQLite (JSON on stdout).",
    )
    p_runs.add_argument(
        "--limit",
        type=_positive_int("limit"),
        default=20,
        metavar="N",
        help="Maximum number of runs to return (newest first). Default: 20.",
    )

    p_status = sub.add_parser(
        "status",
        help="Per-stage status for a run (JSON on stdout).",
    )
    p_status.add_argument(
        "run_id",
        help="Run identifier (UUID from pharma-rd run or runs list).",
    )

    sub.add_parser(
        "scheduler",
        help=(
            "In-process cron scheduler for recurring pipeline runs (FR2 / Epic 2)."
        ),
    )

    p_retry = sub.add_parser(
        "retry-stage",
        help="Resume a failed run from a failed stage using saved artifacts (FR30).",
    )
    p_retry.add_argument(
        "run_id",
        help="Existing run identifier (UUID).",
    )
    p_retry.add_argument(
        "stage_key",
        metavar="STAGE",
        help="Stage to re-run: clinical|competitor|consumer|synthesis|delivery.",
    )

    args = parser.parse_args()
    if args.command == "run":
        from pharma_rd.cli import run_foreground_pipeline

        return run_foreground_pipeline()
    if args.command == "runs":
        from pharma_rd.cli import cmd_runs

        return cmd_runs(limit=args.limit)
    if args.command == "status":
        from pharma_rd.cli import cmd_status

        return cmd_status(args.run_id)
    if args.command == "scheduler":
        from pharma_rd.scheduler import run_scheduler

        return run_scheduler()
    if args.command == "retry-stage":
        from pharma_rd.cli import cmd_retry_stage

        return cmd_retry_stage(args.run_id, args.stage_key)

    parser.print_help()
    return 0


def main() -> None:
    try:
        code = main_exit_code()
    except ValidationError as e:
        print(str(e), file=sys.stderr)
        raise SystemExit(1) from None
    raise SystemExit(code)
