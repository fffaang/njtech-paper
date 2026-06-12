from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MIN_PYTHON = (3, 11)
DEFAULT_TIMEOUT = 600
CHINA_PYPI_INDEX = "https://pypi.tuna.tsinghua.edu.cn/simple"
CHINA_PYPI_HOST = "pypi.tuna.tsinghua.edu.cn"
FIXED_SCANSCI_COMMIT = "8963533f5eb84b6cdd99f89ec94916ed0ca9acbc"
FIXED_SCANSCI_URL = f"https://github.com/fffaang/njtech-paper/archive/{FIXED_SCANSCI_COMMIT}.zip"
FALLBACK_PACKAGE_SPEC = f"scansci-pdf @ {FIXED_SCANSCI_URL}"
PYPI_DEPENDENCIES = [
    "requests>=2.31",
    "requests[socks]>=2.31",
    "beautifulsoup4>=4.12",
    "mcp[cli]>=1.12",
    "typer>=0.15",
    "uvicorn>=0.34",
    "pycryptodome>=3.20",
    "selenium>=4.15",
    "cloakbrowser>=0.3",
    "pypdf",
]
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


class BootstrapError(RuntimeError):
    """Base class for setup failures with a human-readable stage."""

    def __init__(self, stage: str, message: str):
        super().__init__(message)
        self.stage = stage


class CommandFailed(BootstrapError):
    pass


class CommandTimedOut(BootstrapError):
    pass


def data_dir() -> Path:
    configured = os.environ.get("SCANSCI_PDF_DATA_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".scansci-pdf"


def config_path() -> Path:
    return data_dir() / "config.json"


def default_log_path() -> Path:
    return data_dir() / "bootstrap.log"


class Logger:
    def __init__(self, path: Path, *, dry_run: bool):
        self.path = path
        self.dry_run = dry_run
        if dry_run:
            print(f"[dry-run] bootstrap.log would be written to: {path}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("", encoding="utf-8")

    def log(self, message: str) -> None:
        print(message)
        if self.dry_run:
            return
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(f"{timestamp} {message}\n")


def _mask_proxy(value: str) -> str:
    if "://" in value and "@" in value:
        scheme, rest = value.split("://", 1)
        return f"{scheme}://***@{rest.split('@', 1)[1]}"
    return value


def _display_command(args: list[str]) -> str:
    safe_args: list[str] = []
    mask_next = False
    for arg in args:
        if mask_next:
            safe_args.append(_mask_proxy(arg))
            mask_next = False
            continue
        safe_args.append(arg)
        if arg == "--proxy":
            mask_next = True
    return subprocess.list2cmdline(safe_args)


def run_command(
    args: list[str],
    *,
    dry_run: bool,
    logger: Logger,
    stage: str,
    timeout: int,
) -> None:
    display = _display_command(args)
    logger.log(f"[stage] {stage}")
    logger.log(f"[run] {display}")
    if dry_run:
        logger.log("[dry-run] would run command")
        return

    start = time.monotonic()
    try:
        completed = subprocess.run(args, check=False, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        elapsed = time.monotonic() - start
        raise CommandTimedOut(
            stage,
            f"{stage} timed out after {elapsed:.1f}s (limit {timeout}s).",
        ) from exc

    elapsed = time.monotonic() - start
    logger.log(f"[done] {stage}: exit={completed.returncode}, elapsed={elapsed:.1f}s")
    if completed.returncode != 0:
        raise CommandFailed(stage, f"{stage} failed with exit code {completed.returncode}.")


def check_python_version(logger: Logger) -> None:
    logger.log(f"[python] executable: {sys.executable}")
    logger.log(f"[python] version: {sys.version.split()[0]}")
    if sys.version_info < MIN_PYTHON:
        current = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        required = ".".join(str(part) for part in MIN_PYTHON)
        raise SystemExit(f"Python {required}+ is required; current Python is {current}")


def pip_install_args(
    packages: list[str],
    *,
    china_mirror: bool,
    proxy: str | None,
    no_deps: bool = False,
) -> list[str]:
    python = sys.executable
    args = [
        python,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "--prefer-binary",
        "--retries",
        "5",
        "--timeout",
        "60",
    ]
    if no_deps:
        args.append("--no-deps")
    if china_mirror:
        args.extend(["--index-url", CHINA_PYPI_INDEX, "--trusted-host", CHINA_PYPI_HOST])
    if proxy:
        args.extend(["--proxy", proxy])
    args.extend(packages)
    return args


def run_pip_install(
    packages: list[str],
    *,
    dry_run: bool,
    logger: Logger,
    stage: str,
    timeout: int,
    china_mirror: bool,
    proxy: str | None,
    no_deps: bool = False,
) -> None:
    args = pip_install_args(packages, china_mirror=china_mirror, proxy=proxy, no_deps=no_deps)
    run_command(args, dry_run=dry_run, logger=logger, stage=stage, timeout=timeout)


def find_vendor_wheel() -> Path | None:
    vendor = ROOT / "vendor"
    wheels = sorted(vendor.glob("scansci_pdf-*.whl"))
    if not wheels:
        return None
    if len(wheels) > 1:
        names = ", ".join(wheel.name for wheel in wheels)
        raise SystemExit(f"Expected exactly one vendor wheel, found: {names}")
    return wheels[0]


def verify_vendor_wheel(wheel: Path) -> None:
    checksum_path = wheel.with_suffix(wheel.suffix + ".sha256")
    if not checksum_path.exists():
        raise SystemExit(f"Missing checksum file for vendor wheel: {checksum_path}")
    expected = checksum_path.read_text(encoding="utf-8").split()[0].lower()
    actual = hashlib.sha256(wheel.read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit(f"Vendor wheel checksum mismatch: expected {expected}, got {actual}")


def install_dependencies(
    *,
    dry_run: bool,
    logger: Logger,
    timeout: int,
    china_mirror: bool,
    proxy: str | None,
) -> None:
    run_command(
        [sys.executable, "-m", "pip", "--version"],
        dry_run=dry_run,
        logger=logger,
        stage="Check pip",
        timeout=60,
    )

    try:
        run_pip_install(
            ["pip", "setuptools", "wheel"],
            dry_run=dry_run,
            logger=logger,
            stage="Upgrade pip/setuptools/wheel",
            timeout=timeout,
            china_mirror=china_mirror,
            proxy=proxy,
        )
    except BootstrapError:
        if china_mirror:
            raise
        logger.log("[retry] pip/setuptools/wheel upgrade failed; retrying with Tsinghua mirror.")
        run_pip_install(
            ["pip", "setuptools", "wheel"],
            dry_run=dry_run,
            logger=logger,
            stage="Upgrade pip/setuptools/wheel with Tsinghua mirror",
            timeout=timeout,
            china_mirror=True,
            proxy=proxy,
        )

    try:
        run_pip_install(
            PYPI_DEPENDENCIES,
            dry_run=dry_run,
            logger=logger,
            stage="Install PyPI dependencies for legal NJTech access",
            timeout=timeout,
            china_mirror=china_mirror,
            proxy=proxy,
        )
    except BootstrapError:
        if china_mirror:
            raise
        logger.log("[retry] PyPI dependency install failed; retrying with Tsinghua mirror.")
        run_pip_install(
            PYPI_DEPENDENCIES,
            dry_run=dry_run,
            logger=logger,
            stage="Install PyPI dependencies with Tsinghua mirror",
            timeout=timeout,
            china_mirror=True,
            proxy=proxy,
        )

    wheel = find_vendor_wheel()
    if wheel:
        verify_vendor_wheel(wheel)
        logger.log(f"[vendor] installing local wheel: {wheel}")
        run_pip_install(
            [str(wheel)],
            dry_run=dry_run,
            logger=logger,
            stage="Install vendored scansci-pdf wheel",
            timeout=timeout,
            china_mirror=china_mirror,
            proxy=proxy,
            no_deps=True,
        )
        return

    logger.log("[fallback] Local vendor wheel is missing; GitHub archive install may be slow.")
    run_pip_install(
        [FALLBACK_PACKAGE_SPEC],
        dry_run=dry_run,
        logger=logger,
        stage="Install fixed scansci-pdf from GitHub archive fallback",
        timeout=timeout,
        china_mirror=False,
        proxy=proxy,
        no_deps=True,
    )


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


def write_config(*, dry_run: bool, logger: Logger) -> None:
    path = config_path()
    existing = load_existing_config(path)
    merged = dict(existing)
    merged.update(NJTECH_CONFIG)

    logger.log(f"[config] target: {path}")
    for key in sorted(NJTECH_CONFIG):
        logger.log(f"[config] {key}={merged[key]!r}")

    if dry_run:
        logger.log("[dry-run] would merge NJTech legal-only config")
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")


def run_scansci_check(*, dry_run: bool, logger: Logger, timeout: int) -> None:
    if module_available("scansci_pdf.main"):
        run_command(
            [sys.executable, "-m", "scansci_pdf.main", "check"],
            dry_run=dry_run,
            logger=logger,
            stage="Run scansci-pdf check",
            timeout=timeout,
        )
        return

    command = shutil.which("scansci-pdf")
    if command:
        run_command(
            [command, "check"],
            dry_run=dry_run,
            logger=logger,
            stage="Run scansci-pdf check",
            timeout=timeout,
        )
        return

    run_command(
        [sys.executable, "-m", "scansci_pdf.main", "check"],
        dry_run=dry_run,
        logger=logger,
        stage="Run scansci-pdf check",
        timeout=timeout,
    )


def warmup_browser(*, dry_run: bool, logger: Logger, timeout: int) -> None:
    logger.log(
        "[warmup] first Camofox launch downloads Chromium (~200MB) and caches it locally; this is not pip install."
    )
    code = (
        "from cloakbrowser import launch; "
        "browser = launch(headless=True); "
        "browser.close(); "
        "print('cloakbrowser warmup ok')"
    )
    run_command(
        [sys.executable, "-c", code],
        dry_run=dry_run,
        logger=logger,
        stage="Warm up CloakBrowser browser binary",
        timeout=timeout,
    )


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
    parser.add_argument(
        "--china-mirror",
        action="store_true",
        help="Use the Tsinghua PyPI mirror for PyPI dependencies.",
    )
    parser.add_argument(
        "--proxy",
        help="Proxy URL used only for pip installation, for example http://127.0.0.1:7890.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Per-stage timeout in seconds. Default: {DEFAULT_TIMEOUT}.",
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=None,
        help="Path for bootstrap.log. Default: ~/.scansci-pdf/bootstrap.log.",
    )
    parser.add_argument(
        "--warmup-browser",
        action="store_true",
        help="After setup, launch CloakBrowser once to download/cache its Chromium binary.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logger = Logger(args.log or default_log_path(), dry_run=args.dry_run)
    logger.log("[njtech-paper] Bootstrap legal NJTech paper access")
    logger.log("[njtech-paper] This script does not ask for or save your NJTech password.")
    logger.log("[njtech-paper] It does not enable Sci-Hub, LibGen, or Tor.")
    logger.log(f"[njtech-paper] bootstrap.log: {logger.path}")

    try:
        check_python_version(logger)

        if not args.skip_install:
            install_dependencies(
                dry_run=args.dry_run,
                logger=logger,
                timeout=args.timeout,
                china_mirror=args.china_mirror,
                proxy=args.proxy,
            )
        else:
            logger.log("[skip] dependency installation")

        write_config(dry_run=args.dry_run, logger=logger)

        if not args.skip_check:
            run_scansci_check(dry_run=args.dry_run, logger=logger, timeout=args.timeout)
        else:
            logger.log("[skip] scansci-pdf check")

        if args.warmup_browser:
            warmup_browser(dry_run=args.dry_run, logger=logger, timeout=args.timeout)
        else:
            logger.log(
                "[note] first Camofox launch downloads Chromium (~200MB) if not cached; use --warmup-browser to do it now."
            )

    except BootstrapError as exc:
        logger.log(f"[error] {exc}")
        logger.log("[hint] If PyPI dependency download is slow, rerun with --china-mirror.")
        logger.log("[hint] If Codex needs a proxy, rerun with --proxy http://127.0.0.1:<port>.")
        logger.log(
            "[hint] If setup passed but the browser seems slow, the first Camofox launch downloads Chromium (~200MB)."
        )
        logger.log(f"[hint] Full log: {logger.path}")
        return 1

    logger.log("[njtech-paper] Setup complete. Use your own NJTech account only on official login pages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
