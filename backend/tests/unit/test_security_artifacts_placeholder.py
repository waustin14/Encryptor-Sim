from pathlib import Path


def test_security_artifacts_placeholders_listed() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    readme_path = repo_root / "docs" / "security" / "README.md"

    assert readme_path.exists(), "docs/security/README.md must exist"
    content = readme_path.read_text(encoding="utf-8")

    for token in ["nmap-", "zap-", "sqlmap-"]:
        assert token in content, f"Missing artifact placeholder: {token}"
