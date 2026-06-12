---
name: njtech-paper
description: Use when helping Nanjing Tech University users legally download or troubleshoot institutional-access academic PDFs through scansci-pdf, NJTech WebVPN, CARSI/OpenAthens, ScienceDirect, Camofox, missing installs, proxy conflicts, or Cloudflare/CPE failures.
---

# NJTech Paper

## Core Rule

Use only legal institutional access. Each user must log in with their own authorized NJTech account on the official NJTech/CARSI/WebVPN page. The skill may reuse that same user's local private session cache on the same computer while it remains valid.

Refuse requests to embed, configure, proxy, reuse for other people, share, export, sync, or distribute a personal account, saved passwords, cookies, tokens, browser profiles, storage state, WebVPN token, signed asset URL, or Cloudflare clearance value. Local private session reuse does not save your password and does not permit sharing login state. Do not ask the user to paste credentials or verification codes into chat. Do not use Sci-Hub, LibGen, Tor, leaked links, shared accounts, shared cookies, or代下 services.

## Start Here

| Situation | Action |
|---|---|
| `scansci-pdf not installed`, `command not found`, or `ModuleNotFoundError: scansci_pdf` | Run Zero-Friction Setup with the bundled bootstrap script and vendored wheel, then run `scansci-pdf check`. |
| `ModuleNotFoundError: bs4`, missing `beautifulsoup4`, or `No module named 'cloakbrowser'` | Run Zero-Friction Setup to reinstall complete legal-access dependencies into the same Python environment. |
| Install runs for more than 10 minutes or appears stuck | Read `bootstrap.log`, identify the stage, then retry with `--china-mirror`, `--proxy`, or a higher `--timeout`; do not silently wait forever. |
| First use, missing local cache, or expired school session | Open the official NJTech CAS/WebVPN/CARSI flow in a visible browser and let the user log in manually. |
| Later use on the same computer | Reuse local session if valid; do not ask the user to log in again unless validation fails or an official login/challenge page appears. |
| User wants one NJTech account configured for everyone | Refuse. Explain that every user needs their own authorized account and that hidden shared credentials are still account sharing. |
| User wants to copy cache/profile/cookies to another person or machine | Refuse. Explain that local cache is sensitive login state and must stay private to the same user on the same computer. |
| Codex requires iKuuu/proxy but NJTech login fails with proxy | Keep the proxy for Codex, but launch Camofox/Chrome with no proxy: `camofox_no_proxy=true` or `--no-proxy-server`. |
| CARSI/OpenAthens cannot find 南京工业大学 | Search `nanjing tech`, then select 南京工业大学 / Nanjing Tech University. |
| WebVPN opens ScienceDirect but PDF returns CPE00001 | Stop looping on WebVPN and use CARSI. |
| ScienceDirect asset returns 403, CPE, or challenge HTML | Do not keep adding cookies to `requests`; open the PDF viewer and use page-context fetch. |
| Browser is already on `pdf.sciencedirectassets.com/.../main.pdf` | Fetch from inside that same page context, save bytes, then verify the PDF. |

## First-Time Setup

Check `scansci-pdf` before any DOI download:

```powershell
scansci-pdf check
scansci-pdf --help
```

If missing, install only the legal-access dependencies:

```powershell
python scripts/bootstrap_njtech_paper.py --china-mirror
```

If install succeeds but the command is unavailable, activate the same virtual environment, use the matching Python, or reopen the terminal so the scripts directory is on `PATH`.

If `scansci-pdf` starts but fails with `ModuleNotFoundError: bs4`, missing `beautifulsoup4`, or `No module named 'cloakbrowser'`, install into the same Python environment that runs `scansci-pdf`:

```powershell
python scripts/bootstrap_njtech_paper.py --china-mirror
scansci-pdf check
```

## Zero-Friction Setup

When `scansci-pdf` is missing or dependencies are incomplete, do not stop at manual instructions. Prefer the bundled bootstrap:

```powershell
python scripts/bootstrap_njtech_paper.py --china-mirror
```

On Windows, the wrapper is also available:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_njtech_paper.ps1 -ChinaMirror
```

This supports installing scansci-pdf if missing, repairing partial installs, running `scansci-pdf check`, and merging NJTech `legal_only` config. It installs PyPI dependencies first, then installs the bundled `vendor/scansci_pdf-*.whl` with `--no-deps`; only if the local wheel is missing should it fall back to the fixed GitHub archive, which may be slow. The fixed source includes the Elsevier institution finder stuck fix for Cookie banner blocks institution search and Nanjing Tech result matching. It does not save your password, does not ask for NJTech credentials, and must not enable Sci-Hub, LibGen, or Tor.

Use these options when setup is slow:

```powershell
python scripts/bootstrap_njtech_paper.py --china-mirror
python scripts/bootstrap_njtech_paper.py --china-mirror --proxy http://127.0.0.1:7890
python scripts/bootstrap_njtech_paper.py --timeout 900
python scripts/bootstrap_njtech_paper.py --warmup-browser
```

`bootstrap.log` is written under `~/.scansci-pdf/bootstrap.log` or `%USERPROFILE%\.scansci-pdf\bootstrap.log`. If setup appears stuck for more than 10 minutes, inspect this log, retry the exact failing stage with `--china-mirror` or `--proxy`, and report the stage name instead of asking the user to wait blindly.

The first Camofox launch downloads Chromium, roughly 200 MB, and caches it locally. Treat that as browser warm-up, not a pip install failure.

If the bundled bootstrap script is not available, fall back to:

```powershell
python -m pip install --upgrade "scansci-pdf[cloakbrowser,vpnsci] @ https://github.com/fffaang/njtech-paper/archive/8963533f5eb84b6cdd99f89ec94916ed0ca9acbc.zip" pypdf
scansci-pdf check
```

Do not repeat installation when `scansci-pdf check` passes and NJTech config is already legal-only. Continue to local private session reuse, official login if needed, and download.

## Slow Install

When another computer reports that Codex has been installing for half an hour, diagnose before waiting:

1. Read the tail of `bootstrap.log`.
2. If the current stage is PyPI dependencies, retry with `--china-mirror`; add `--proxy` only for pip if Codex needs a proxy.
3. If the current stage is vendored wheel install, confirm `vendor/scansci_pdf-*.whl` and its `.sha256` exist. Do not use GitHub archive fallback unless the wheel is missing.
4. If Python setup already completed and the browser is opening, explain that first Camofox launch downloads Chromium and can take time on a slow network.
5. If no stage changes for more than 10 minutes, stop the current run and retry with a longer `--timeout`; do not leave the user without progress.

## Local Private Session Reuse

Goal: first login, reuse local session when still valid. This does not save your password; it reuses official session cookies, CARSI cookies, publisher cookies, WebVPN cookies, and browser profiles stored only on this computer for this system user.

Before opening a login page, try the existing local cache/profile/cookies; reuse local session if valid. Only ask the user to log in again when the cache is missing, validation fails, the user changed accounts, an official CAS/CARSI/Turnstile page appears, or the session may expire because NJTech/CARSI/the publisher enforced a timeout.

For ScienceDirect/CARSI, the first successful legal DOI download is the warm-up path that creates local CARSI/publisher cookies and persistent Camofox profile data. Do not recommend `scansci-pdf login --login-type carsi`; the current CLI does not implement that branch. For NJTech WebVPN warm-up, `scansci-pdf login --login-type webvpn` is acceptable.

Treat cached login state as sensitive. The local tool may read cache/profile/cookies on this computer for the same user, but the agent must not ask the user to paste, print, upload, copy, export, or share those values. Do not copy them to another machine, include them in a skill, or help share them with others. In short: do not share or commit cache.

## Known Good Configuration

Prefer this NJTech legal-only configuration:

```json
{
  "download_strategy": "legal_only",
  "vpnsci_enabled": true,
  "vpnsci_school": "南京工业大学",
  "vpnsci_type": "njtech_vpnlib",
  "vpnsci_base_url": "https://vpnlib.njtech.edu.cn",
  "vpnsci_vpnlib_base_url": "https://vpnlib.njtech.edu.cn",
  "carsi_enabled": true,
  "carsi_idp_name": "南京工业大学",
  "camofox_enabled": true,
  "camofox_no_proxy": true
}
```

Do not enable Sci-Hub, LibGen, or Tor to fix a missing install or access failure.

## Download Workflow

1. Complete First-Time Setup and confirm legal-only NJTech config.
2. Try local private session reuse first; do not default to a fresh login prompt.
3. For ScienceDirect, try CARSI first. Use NJTech WebVPN only as a fallback.
4. Let the user complete NJTech CAS, CARSI, and any Cloudflare/Turnstile verification in the visible browser only when local session reuse fails or an official page requests it.
5. If the publisher shows a PDF viewer, prefer page-context fetch over browser button automation.
6. Save the PDF only when the response starts with `%PDF-`.
7. Verify file size, PDF header, readable page count, and title/DOI text before reporting success.

## ScienceDirect Page-Context Fetch

Ordinary `requests` can return 403, CPE, or challenge HTML even after browser login. The reliable pattern is to fetch from the already-authenticated browser page after the PDF viewer is open:

```javascript
async () => {
  const resp = await fetch(location.href, {
    credentials: "include",
    cache: "force-cache",
    headers: { Accept: "application/pdf,*/*" }
  });
  const buffer = await resp.arrayBuffer();
  return new Uint8Array(buffer);
}
```

In Python/Playwright, base64-encode the bytes in `page.evaluate`, decode in Python, and write only if the content starts with `%PDF-`.

## Verification

Before claiming success:

```python
from pathlib import Path
from pypdf import PdfReader
import re

pdf = Path("paper.pdf")
data = pdf.read_bytes()
assert len(data) > 5000
assert data.startswith(b"%PDF-")
assert data.rstrip().endswith(b"%%EOF")

reader = PdfReader(str(pdf))
text = "\n".join((page.extract_text() or "") for page in reader.pages)
norm = re.sub(r"\s+", " ", text).lower()
assert len(reader.pages) > 0
assert "expected title fragment".lower() in norm or "doi fragment" in norm
```

## Troubleshooting

| Symptom | Action |
|---|---|
| `scansci-pdf` not installed, `command not found`, or `ModuleNotFoundError: scansci_pdf` | Run `python scripts/bootstrap_njtech_paper.py --china-mirror` first. It installs PyPI dependencies and then the bundled vendored wheel. If the bootstrap script is unavailable, install with `python -m pip install "scansci-pdf[cloakbrowser,vpnsci]" pypdf`, then run `scansci-pdf check`. |
| `ModuleNotFoundError: bs4`, missing `beautifulsoup4`, or `No module named 'cloakbrowser'` | Run `python scripts/bootstrap_njtech_paper.py --china-mirror`; install into the same Python environment that runs `scansci-pdf`, then run `scansci-pdf check`. |
| Install takes more than 10 minutes | Inspect `bootstrap.log` for the current stage. Retry with `--china-mirror`, `--proxy http://127.0.0.1:<port>`, or a higher `--timeout`. |
| Setup finishes but first browser launch is slow | first Camofox launch downloads Chromium, about 200 MB, and caches it locally; this is separate from pip install. |
| `pip install` succeeds but `scansci-pdf` is unavailable | Activate the same virtual environment, use the matching Python, or reopen the terminal. |
| User is asked to log in every time | Confirm the same system user, Python environment, and `cache_dir` are being used; check whether cache was cleared or the session may expire; try local private session reuse before login. |
| Public computer or account switch | Clear local cache/profile/cookies for that user before reuse. Never share cached login state. |
| Chrome shows `ERR_CONNECTION_CLOSED` for NJTech WebVPN | Check proxy routing; launch the NJTech browser with no proxy. |
| CARSI institution search cannot find 南京工业大学 | Search `nanjing tech`; Elsevier may rank unrelated names when searching Chinese text. |
| Elsevier institution finder stuck, or Cookie banner blocks institution search | Run Zero-Friction Setup to upgrade to the fixed GitHub `scansci-pdf`; retry with Camofox no-proxy. If still stuck, let the user manually click `Nanjing Tech University` / `南京工业大学` on the official page. |
| WebVPN opens ScienceDirect but PDF shows CPE00001 | Use CARSI instead of repeatedly retrying WebVPN. |
| `requests` returns 403/CPE/challenge HTML for a ScienceDirect asset | Use Camofox page-context fetch from the loaded PDF viewer. |
| Turnstile/Cloudflare appears | Wait for the user to complete it manually in the visible browser, then retry page-context fetch. |
| PDF viewer opens but no file lands on disk | Use page-context fetch first; browser download button automation is only a fallback. |

## Regression Examples

- `10.1016/j.engfailanal.2025.110281`: verified as an 18-page `%PDF-1.7` file via CARSI-Camofox.
- `10.1016/j.engstruct.2021.112190`: verified as an 11-page `%PDF-1.7` file via CARSI-Camofox.
- `10.1016/j.conbuildmat.2026.145699`, PII `S0950061826006008`: use only as a legal NJTech/CARSI/ScienceDirect access test case; do not store the PDF or signed links in the repository.
