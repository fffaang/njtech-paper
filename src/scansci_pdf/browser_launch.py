"""Shared browser launch options for CloakBrowser/Camofox."""

from __future__ import annotations

from typing import Any


def camofox_launch_args(config: dict[str, Any] | None = None, extra: list[str] | None = None) -> list[str]:
    """Return Chromium args for scansci-pdf controlled browser windows."""
    args = ["--disable-features=CrossOriginOpenerPolicy"]
    if config and config.get("camofox_no_proxy"):
        args.append("--no-proxy-server")
    if extra:
        args.extend(extra)
    return args
