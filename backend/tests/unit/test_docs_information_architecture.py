from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_required_docs_are_present() -> None:
    root = _repo_root()
    required = [
        root / "docs" / "user-guide.md",
        root / "docs" / "api-reference.md",
        root / "docs" / "architecture.md",
        root / "docs" / "ports-protocols.md",
        root / "docs" / "security-report.md",
    ]

    for path in required:
        assert path.exists(), f"Required documentation file missing: {path}"


def test_readme_files_expose_canonical_doc_entry_points() -> None:
    root = _repo_root()
    root_readme = (root / "README.md").read_text(encoding="utf-8")
    docs_readme = (root / "docs" / "README.md").read_text(encoding="utf-8")

    for token in [
        "docs/README.md",
        "docs/user-guide.md",
        "docs/api-reference.md",
        "docs/architecture.md",
        "docs/ports-protocols.md",
        "docs/security-report.md",
    ]:
        assert token in root_readme, f"Root README missing docs token: {token}"

    for token in [
        "user-guide.md",
        "api-reference.md",
        "architecture.md",
        "ports-protocols.md",
        "security-report.md",
    ]:
        assert token in docs_readme, f"Docs README missing docs token: {token}"


def test_architecture_and_ports_docs_are_not_placeholder_only() -> None:
    root = _repo_root()
    for path in [
        root / "docs" / "architecture.md",
        root / "docs" / "ports-protocols.md",
    ]:
        content = path.read_text(encoding="utf-8")
        assert "Placeholder" not in content
        assert len(content.strip()) >= 400, f"{path} is too short to be complete"


def test_user_guide_covers_v1_operational_workflows() -> None:
    root = _repo_root()
    user_guide = (root / "docs" / "user-guide.md").read_text(encoding="utf-8")

    for token in [
        "/login",
        "/change-password",
        "/dashboard",
        "/interfaces",
        "/peers",
        "/routes",
        "screenshot",
        "image/",
        "JWT",
        "self-signed",
        "MGMT",
    ]:
        assert token in user_guide, f"User guide missing required token: {token}"


def test_user_guide_screenshot_assets_exist() -> None:
    root = _repo_root()
    screenshots = [
        root / "image" / "user-guide-login.png",
        root / "image" / "user-guide-change-password.png",
        root / "image" / "user-guide-dashboard.png",
        root / "image" / "user-guide-interfaces.png",
        root / "image" / "user-guide-peers.png",
        root / "image" / "user-guide-routes.png",
        root / "image" / "user-guide-logout.png",
    ]

    for screenshot in screenshots:
        assert screenshot.exists(), f"Missing screenshot asset: {screenshot}"
        assert screenshot.stat().st_size > 0, f"Empty screenshot asset: {screenshot}"


def test_architecture_doc_has_diagram_and_planning_cross_link() -> None:
    root = _repo_root()
    architecture_doc = (root / "docs" / "architecture.md").read_text(encoding="utf-8")

    for token in [
        "```mermaid",
        "CT",
        "PT",
        "MGMT",
        "_bmad-output/planning-artifacts/architecture.md",
    ]:
        assert token in architecture_doc, f"Architecture doc missing token: {token}"


def test_ports_protocols_doc_covers_required_services_and_checks() -> None:
    root = _repo_root()
    ports_doc = (root / "docs" / "ports-protocols.md").read_text(encoding="utf-8")
    ports_doc_lower = ports_doc.lower()

    for token in [
        "tcp 443",
        "udp 500",
        "udp 4500",
        "protocol 50",
        "/api/v1/ws",
        "directionality",
        "security implication",
        "firewall",
        "validation checklist",
    ]:
        assert token in ports_doc_lower, f"Ports/protocols doc missing token: {token}"
