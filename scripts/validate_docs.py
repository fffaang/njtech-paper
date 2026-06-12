from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PHRASES = {
    "README.md": [
        "## Quick Start",
        "## Example Prompts",
        "## Local Private Session Reuse",
        "## FAQ",
        "nanjing tech",
        "camofox_no_proxy=true",
        "10.1016/j.conbuildmat.2026.145699",
        "S0950061826006008",
        "Do not configure one person's NJTech account for everyone",
        "The agent should not ask for or store credentials",
        "does not save your password",
        "reuse local session if valid",
        "session may expire",
        "do not share or commit cache",
        "ModuleNotFoundError: bs4",
        "No module named 'cloakbrowser'",
        "install into the same Python environment",
        "bootstrap_njtech_paper.py",
        "install_njtech_paper.ps1",
        "installing scansci-pdf if missing",
        "## Zero-Friction Setup",
        "## Slow Install",
        "first Camofox launch",
        "downloads Chromium",
        "--china-mirror",
        "--proxy",
        "bootstrap.log",
        "vendor/scansci_pdf-*.whl",
        "--no-deps",
        "Elsevier institution finder stuck",
        "Cookie banner blocks institution search",
        "playwright",
        "manual_verification_required",
        "legal_only no Sci-Hub/Tor hints",
        "S0263822321002385",
    ],
    "SKILL.md": [
        "## Start Here",
        "## Zero-Friction Setup",
        "## Local Private Session Reuse",
        "scansci-pdf not installed",
        "shared accounts",
        "saved passwords",
        "page-context fetch",
        "camofox_no_proxy=true",
        "nanjing tech",
        "10.1016/j.conbuildmat.2026.145699",
        "S0950061826006008",
        "does not save your password",
        "reuse local session if valid",
        "session may expire",
        "do not share or commit cache",
        "ModuleNotFoundError: bs4",
        "No module named 'cloakbrowser'",
        "install into the same Python environment",
        "bootstrap_njtech_paper.py",
        "install_njtech_paper.ps1",
        "installing scansci-pdf if missing",
        "## Slow Install",
        "first Camofox launch",
        "downloads Chromium",
        "--china-mirror",
        "--proxy",
        "bootstrap.log",
        "vendor/scansci_pdf-*.whl",
        "--no-deps",
        "Elsevier institution finder stuck",
        "Cookie banner blocks institution search",
        "playwright",
        "manual_verification_required",
        "legal_only no Sci-Hub/Tor hints",
        "S0263822321002385",
        "Are you a robot?",
    ],
    "SECURITY.md": [
        "Do Not Commit",
        "Account Sharing",
        "Local Private Session Reuse",
        "Do not configure one person's NJTech account for everyone",
        "browser profiles",
        "signed ScienceDirect asset URLs",
        "Downloaded paper PDFs",
        "does not save your password",
        "reuse local session if valid",
        "session may expire",
        "do not share or commit cache",
        "manual_verification_required",
    ],
    "scripts/bootstrap_njtech_paper.py": [
        "FIXED_SCANSCI_COMMIT",
        "0dead208310441dd406541d7b98644710d530d0c",
        "VENDOR_MISSING_MESSAGE",
        "find_vendor_wheel",
        "--no-deps",
        "--china-mirror",
        "--proxy",
        "bootstrap.log",
        "CommandTimedOut",
        "DEFAULT_TIMEOUT",
        "first Camofox launch",
        "downloads Chromium",
        "playwright>=1.45",
    ],
    "scripts/install_njtech_paper.ps1": [
        "ChinaMirror",
        "Proxy",
        "TimeoutSeconds",
        "Log",
        "WarmupBrowser",
    ],
    "vendor/README.md": [
        "Vendored scansci-pdf Wheel",
        "0dead208310441dd406541d7b98644710d530d0c",
        "scansci_pdf-1.5.0-py3-none-any.whl",
        "SHA256",
    ],
}

REQUIRED_FILES = [
    "scripts/bootstrap_njtech_paper.py",
    "scripts/install_njtech_paper.ps1",
    "vendor/README.md",
]

GITIGNORE_REQUIRED = [
    ".scansci-pdf/",
    "cache/",
    "publisher_profile_*",
    "browser_state*.json",
    "carsi_cookies/",
    "publisher_cookies.*",
    "vpnsci-cookies.*",
    "storage_state*.json",
]

FORBIDDEN_PATTERNS = {
    "Cloudflare clearance": re.compile(r"cf_clearance\s*=\s*[^;\s]+", re.I),
    "password assignment": re.compile(r"\bpassword\s*=\s*[^&\s]+", re.I),
    "AWS signed parameter": re.compile(r"\b(?:X-Amz-[A-Za-z0-9-]+|AWSAccessKeyId|Signature=)", re.I),
    "long token": re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{80,}(?![A-Za-z0-9_-])"),
    "cookie/session/token value": re.compile(
        r"\b(?:cookie|session|token|authorization)\s*[:=]\s*['\"]?[A-Za-z0-9._~+/=-]{24,}",
        re.I,
    ),
    "signed ScienceDirect asset URL": re.compile(
        r"https?://pdf\.sciencedirectassets\.com/\S*[?&](?:token|hash|download|expires|X-Amz-|Signature=)",
        re.I,
    ),
    "direct PyPI scansci-pdf fallback in docs": re.compile(
        r"python\s+-m\s+pip\s+install[^\n]*scansci-pdf\[cloakbrowser,vpnsci\]",
        re.I,
    ),
}


def read_required(path: Path) -> str:
    if not path.exists():
        raise AssertionError(f"Missing required file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def check_required_files() -> None:
    missing = [relative for relative in REQUIRED_FILES if not (ROOT / relative).exists()]
    if missing:
        raise AssertionError(f"Missing required files: {missing}")


def check_vendor_wheel() -> None:
    wheels = sorted((ROOT / "vendor").glob("scansci_pdf-*.whl"))
    if len(wheels) != 1:
        raise AssertionError(f"Expected exactly one vendor scansci-pdf wheel, found {len(wheels)}")

    wheel = wheels[0]
    checksum_path = wheel.with_suffix(wheel.suffix + ".sha256")
    if not checksum_path.exists():
        raise AssertionError(f"Missing checksum for vendor wheel: {checksum_path.relative_to(ROOT)}")

    expected = checksum_path.read_text(encoding="utf-8").split()[0].lower()
    actual = hashlib.sha256(wheel.read_bytes()).hexdigest()
    if actual != expected:
        raise AssertionError(
            f"Vendor wheel checksum mismatch for {wheel.name}: expected {expected}, got {actual}"
        )


def check_required_phrases() -> None:
    for relative, phrases in REQUIRED_PHRASES.items():
        text = read_required(ROOT / relative)
        missing = [phrase for phrase in phrases if phrase not in text]
        if missing:
            raise AssertionError(f"{relative} missing phrases: {missing}")


def check_skill_frontmatter() -> None:
    text = read_required(ROOT / "SKILL.md")
    if not text.startswith("---\n"):
        raise AssertionError("SKILL.md frontmatter must start with ---")
    try:
        _, frontmatter, _ = text.split("---\n", 2)
    except ValueError as exc:
        raise AssertionError("SKILL.md frontmatter must be closed with ---") from exc

    fields: dict[str, str] = {}
    for line in frontmatter.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip().strip('"')

    if fields.get("name") != "njtech-paper":
        raise AssertionError("SKILL.md frontmatter must include name: njtech-paper")
    description = fields.get("description", "")
    if not description.startswith("Use when"):
        raise AssertionError("SKILL.md description must start with 'Use when'")


def check_forbidden_patterns() -> None:
    targets = [ROOT / "README.md", ROOT / "SKILL.md", ROOT / "SECURITY.md", ROOT / "vendor" / "README.md"]
    for path in targets:
        text = read_required(path)
        for label, pattern in FORBIDDEN_PATTERNS.items():
            match = pattern.search(text)
            if match:
                snippet = match.group(0)[:80]
                raise AssertionError(f"{path.name} contains forbidden {label}: {snippet!r}")


def check_gitignore_protections() -> None:
    text = read_required(ROOT / ".gitignore")
    missing = [pattern for pattern in GITIGNORE_REQUIRED if pattern not in text]
    if missing:
        raise AssertionError(f".gitignore missing cache/session protections: {missing}")


def main() -> int:
    checks = [
        check_required_files,
        check_vendor_wheel,
        check_required_phrases,
        check_skill_frontmatter,
        check_gitignore_protections,
        check_forbidden_patterns,
    ]
    for check in checks:
        check()
    print("njtech-paper docs validation ok")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
