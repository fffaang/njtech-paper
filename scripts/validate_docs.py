from __future__ import annotations

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
    ],
    "SKILL.md": [
        "## Start Here",
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
    ],
}

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
}


def read_required(path: Path) -> str:
    if not path.exists():
        raise AssertionError(f"Missing required file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


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
    targets = [ROOT / "README.md", ROOT / "SKILL.md", ROOT / "SECURITY.md"]
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
