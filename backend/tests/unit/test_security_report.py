from pathlib import Path


def test_security_report_scope_and_environment_sections() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    report_path = repo_root / "docs" / "security-report.md"

    assert report_path.exists(), "docs/security-report.md must exist"
    content = report_path.read_text(encoding="utf-8")

    required_sections = [
        "## Scope",
        "### Target Surfaces",
        "### Exclusions",
        "## Environment",
        "### Build and Configuration",
    ]
    for section in required_sections:
        assert section in content, f"Missing section: {section}"

    for token in ["MGMT interface", "REST API", "Web UI", "WebSocket"]:
        assert token in content, f"Missing target surface: {token}"

    for token in ["non-destructive", "lab-only"]:
        assert token in content, f"Missing constraint: {token}"

    for token in ["Build ID", "Image SHA", "Configuration"]:
        assert token in content, f"Missing build metadata field: {token}"
