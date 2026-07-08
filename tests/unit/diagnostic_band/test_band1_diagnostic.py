"""Band-1 diagnostic subsystem: kernel-truth status aggregation + panel."""

from __future__ import annotations

from sb.domain.diagnostic.service import ai_diagnostics, platform_status


def test_platform_status_shape():
    status = platform_status()
    assert status["phase"] in ("STARTING", "RUNNING", "DRAINING",
                               "SHUTTING_DOWN", "RESTARTING", "STOPPED",
                               "CONNECTING", "RECONNECTING")
    assert isinstance(status["declared_settings"], int)
    assert isinstance(status["recent_findings"], list)
    assert isinstance(status["ai"], dict)


def test_ai_diagnostics_reads_the_k10_collector():
    from sb.kernel.ai.diagnostics import get_default_collector, reset_default_collector

    reset_default_collector()
    get_default_collector().record_request(provider_active="deterministic")
    snap = ai_diagnostics()
    assert snap.get("requests_observed", 0) >= 1
    assert snap["provider_active"] == "deterministic"
    reset_default_collector()


def test_findings_surface_in_status():
    from sb.kernel.observability.findings import record_operator_finding

    record_operator_finding(source="tests.diagnostic", severity="warning",
                            summary="probe", detail="probe detail",
                            correlation_id=None)
    status = platform_status()
    assert any(f["summary"] == "probe" for f in status["recent_findings"])


def test_diagnostic_panel_and_manifest():
    import sb.manifest.diagnostic as m
    from sb.domain.diagnostic.panels import install_diagnostic_panels
    from tools.manifest_compile import compile_manifests

    assert install_diagnostic_panels().panel_id == "diagnostic.hub"
    m.ENSURE_REFS()
    result = compile_manifests(manifests=[m.MANIFEST])
    assert result.ok, [str(v) for v in result.violations]
