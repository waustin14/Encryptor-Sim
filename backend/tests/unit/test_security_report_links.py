from pathlib import Path


def test_security_report_contains_required_sections_and_links() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    report_path = repo_root / "docs" / "security-report.md"
    docs_readme = repo_root / "docs" / "README.md"
    root_readme = repo_root / "README.md"

    report = report_path.read_text(encoding="utf-8")
    for section in [
        "## Methodology",
        "## Tools and Versions",
        "## Results Summary",
        "## Critical Vulnerabilities",
        "## Isolation Validation Reference",
        "## Risks and Limitations",
        "## Remediation Log",
        "## Raw Artifacts",
    ]:
        assert section in report, f"Missing section: {section}"

    for token in [
        "V1.0",
        "critical",
        "release is blocked",
        "docs/security/README.md",
        "docs/security/scan-results-placeholder.md",
    ]:
        assert token in report, f"Missing report token: {token}"

    assert "security-report.md" in docs_readme.read_text(encoding="utf-8")
    assert "docs/security-report.md" in root_readme.read_text(encoding="utf-8")
