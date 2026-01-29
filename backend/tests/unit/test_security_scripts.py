from pathlib import Path


def test_security_scripts_documented() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    scripts_dir = repo_root / "scripts" / "security"
    readme_path = scripts_dir / "README.md"
    nmap_script = scripts_dir / "run-nmap.sh"
    zap_script = scripts_dir / "run-zap.sh"
    sqlmap_script = scripts_dir / "run-sqlmap.sh"

    assert scripts_dir.exists(), "scripts/security must exist"
    assert readme_path.exists(), "scripts/security/README.md must exist"
    assert nmap_script.exists(), "scripts/security/run-nmap.sh must exist"
    assert zap_script.exists(), "scripts/security/run-zap.sh must exist"
    assert sqlmap_script.exists(), "scripts/security/run-sqlmap.sh must exist"

    readme = readme_path.read_text(encoding="utf-8")
    for token in ["nmap", "OWASP ZAP", "sqlmap", "JWT", "token"]:
        assert token in readme, f"README missing: {token}"
