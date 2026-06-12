from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


MIN_PYTHON = (3, 11)
PACKAGE_SPEC = "scansci-pdf[cloakbrowser,vpnsci]"
NJTECH_CONFIG: dict[str, Any] = {
    "download_strategy": "legal_only",
    "scihub_enabled": False,
    "use_tor_for_scihub": False,
    "vpnsci_enabled": True,
    "vpnsci_school": "南京工业大学",
    "vpnsci_type": "njtech_vpnlib",
    "vpnsci_base_url": "https://vpnlib.njtech.edu.cn",
    "vpnsci_vpnlib_base_url": "https://vpnlib.njtech.edu.cn",
    "carsi_enabled": True,
    "carsi_idp_name": "南京工业大学",
    "camofox_enabled": True,
    "camofox_no_proxy": True,
}


def data_dir() -> Path:
    configured = os.environ.get("SCANSCI_PDF_DATA_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".scansci-pdf"


def config_path() -> Path:
    return data_dir() / "config.json"


def run_command(args: list[str], *, dry_run: bool) -> None:
    printable = " ".join(args)
    if dry_run:
        print(f"[dry-run] would run: {printable}")
        return
    print(f"[run] {printable}")
    subprocess.run(args, check=True)


def check_python_version() -> None:
    if sys.version_info < MIN_PYTHON:
        current = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        required = ".".join(str(part) for part in MIN_PYTHON)
        raise SystemExit(f"Python {required}+ is required; current Python is {current}")


def install_dependencies(*, dry_run: bool) -> None:
    python = sys.executable
    run_command([python, "-m", "pip", "install", "--upgrade", "pip"], dry_run=dry_run)
    run_command([python, "-m", "pip", "install", "--upgrade", PACKAGE_SPEC, "pypdf"], dry_run=dry_run)


def module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except ModuleNotFoundError:
        return False


def load_existing_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Existing config is not valid JSON: {path} ({exc})") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"Existing config must be a JSON object: {path}")
    return data


def write_config(*, dry_run: bool) -> None:
    path = config_path()
    existing = load_existing_config(path)
    merged = dict(existing)
    merged.update(NJTECH_CONFIG)

    print(f"[config] target: {path}")
    for key in sorted(NJTECH_CONFIG):
        print(f"[config] {key}={merged[key]!r}")

    if dry_run:
        print("[dry-run] would merge NJTech legal-only config")
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")


def run_scansci_check(*, dry_run: bool) -> None:
    if module_available("scansci_pdf.main"):
        run_command([sys.executable, "-m", "scansci_pdf.main", "check"], dry_run=dry_run)
        return

    command = shutil.which("scansci-pdf")
    if command:
        run_command([command, "check"], dry_run=dry_run)
        return

    run_command([sys.executable, "-m", "scansci_pdf.main", "check"], dry_run=dry_run)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install and configure njtech-paper dependencies for legal NJTech access.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without installing packages or writing config.",
    )
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Only merge NJTech config and run checks; do not install packages.",
    )
    parser.add_argument(
        "--skip-check",
        action="store_true",
        help="Do not run scansci-pdf check after setup.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    check_python_version()
    print("[njtech-paper] Bootstrap legal NJTech paper access")
    print("[njtech-paper] This script does not ask for or save your NJTech password.")
    print("[njtech-paper] It does not enable Sci-Hub, LibGen, or Tor.")

    if not args.skip_install:
        install_dependencies(dry_run=args.dry_run)
    else:
        print("[skip] dependency installation")

    write_config(dry_run=args.dry_run)

    if not args.skip_check:
        run_scansci_check(dry_run=args.dry_run)
    else:
        print("[skip] scansci-pdf check")

    print("[njtech-paper] Setup complete. Use your own NJTech account only on official login pages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
