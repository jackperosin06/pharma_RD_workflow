"""Round-trip tests for Pydantic stage contracts."""

from __future__ import annotations

from pharma_rd.pipeline.contracts import (
    ClinicalOutput,
    CompetitorOutput,
    ConsumerOutput,
    DeliveryOutput,
    SynthesisOutput,
)


def test_contracts_json_roundtrip() -> None:
    models = [
        ClinicalOutput(run_id="00000000-0000-0000-0000-000000000001"),
        CompetitorOutput(run_id="00000000-0000-0000-0000-000000000002"),
        ConsumerOutput(run_id="00000000-0000-0000-0000-000000000003"),
        SynthesisOutput(),
        DeliveryOutput(),
    ]
    for m in models:
        js = m.model_dump_json()
        assert "schema_version" in js
        assert m.__class__.model_validate_json(js) == m


def test_synthesis_output_v4_json_gets_fr27_fr28_defaults() -> None:
    """On-disk v4 artifacts load with safe FR27/FR28 defaults (re-run for populated)."""
    legacy = (
        '{"schema_version":4,"run_id":"r1","aggregated_upstream_gaps":[],'
        '"ranking_criteria_version":"cross_domain_v1","ranked_opportunities":[],'
        '"note":"stub"}'
    )
    out = SynthesisOutput.model_validate_json(legacy)
    assert out.schema_version == 4
    assert out.signal_characterization == "unknown"
    assert out.scan_summary_lines == []


def test_delivery_output_v1_json_defaults() -> None:
    """Legacy v1 delivery JSON loads with FR18 path fields defaulted."""
    legacy = '{"schema_version":1,"note":"stub"}'
    out = DeliveryOutput.model_validate_json(legacy)
    assert out.schema_version == 1
    assert out.report_relative_path == ""
    assert out.report_byte_size == 0


def test_delivery_output_v3_json_gets_html_defaults() -> None:
    """On-disk v3 delivery JSON without HTML fields loads with empty HTML paths."""
    legacy = (
        '{"schema_version":3,"run_id":"r1","report_relative_path":"r1/delivery/report.md",'
        '"report_format":"markdown","report_byte_size":10,"note":"stub"}'
    )
    out = DeliveryOutput.model_validate_json(legacy)
    assert out.schema_version == 3
    assert out.report_html_relative_path == ""
    assert out.report_html_byte_size == 0


def test_delivery_output_v3_json_gets_slack_defaults() -> None:
    """Legacy delivery JSON without Slack fields loads with safe defaults."""
    legacy = (
        '{"schema_version":3,"run_id":"r1","report_relative_path":"r1/delivery/report.md",'
        '"report_format":"markdown","report_byte_size":10,"distribution_channel":"none",'
        '"distribution_status":"skipped","note":"stub"}'
    )
    out = DeliveryOutput.model_validate_json(legacy)
    assert out.slack_notify_status == "skipped"
    assert out.slack_notify_detail == ""


def test_delivery_output_v2_json_gets_fr19_defaults() -> None:
    """On-disk v2 delivery JSON loads with FR19 distribution fields defaulted."""
    legacy = (
        '{"schema_version":2,"run_id":"r1","report_relative_path":"r1/delivery/report.md",'
        '"report_format":"markdown","report_byte_size":10,"note":"stub"}'
    )
    out = DeliveryOutput.model_validate_json(legacy)
    assert out.schema_version == 2
    assert out.distribution_channel == "none"
    assert out.distribution_status == "skipped"
    assert out.distribution_detail == ""
