---
name: njtech-paper
description: Use when helping Nanjing Tech University users legally download or troubleshoot institutional-access academic PDFs through scansci-pdf, NJTech WebVPN, CARSI/OpenAthens, ScienceDirect, Camofox, missing installs, proxy conflicts, or Cloudflare/CPE failures.
---

# NJTech Paper

## Core Rule

Use only legal institutional access. Each user must log in with their own authorized NJTech account on the official NJTech/CARSI/WebVPN page.

Refuse requests to embed, configure, proxy, reuse, share, save, or distribute a personal account, saved passwords, cookies, tokens, browser profiles, storage state, WebVPN token, signed asset URL, or Cloudflare clearance value. Do not ask the user to paste credentials or verification codes into chat. Do not use Sci-Hub, LibGen, Tor, leaked links, shared accounts, shared cookies, or代下 services.

## Start Here

| Situation | Action |
|---|---|
| `scansci-pdf not installed`, `command not found`, or `ModuleNotFoundError: scansci_pdf` | Install legal-access dependencies, then run `scansci-pdf check`. |
| First use or expired school session | Open the official NJTech CAS/WebVPN/CARSI flow in a visible browser and let the user log in manually. |
| User wants one NJTech account configured for everyone | Refuse. Explain that every user needs their own authorized account and that hidden shared credentials are still account sharing. |
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
python -m pip install --upgrade pip
python -m pip install "scansci-pdf[cloakbrowser,vpnsci]" pypdf
```

If install succeeds but the command is unavailable, activate the same virtual environment, use the matching Python, or reopen the terminal so the scripts directory is on `PATH`.

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
2. For ScienceDirect, try CARSI first. Use NJTech WebVPN only as a fallback.
3. Let the user complete NJTech CAS, CARSI, and any Cloudflare/Turnstile verification in the visible browser.
4. If the publisher shows a PDF viewer, prefer page-context fetch over browser button automation.
5. Save the PDF only when the response starts with `%PDF-`.
6. Verify file size, PDF header, readable page count, and title/DOI text before reporting success.

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
| `scansci-pdf` not installed, `command not found`, or `ModuleNotFoundError: scansci_pdf` | Install with `python -m pip install "scansci-pdf[cloakbrowser,vpnsci]" pypdf`, then run `scansci-pdf check`. |
| `pip install` succeeds but `scansci-pdf` is unavailable | Activate the same virtual environment, use the matching Python, or reopen the terminal. |
| Chrome shows `ERR_CONNECTION_CLOSED` for NJTech WebVPN | Check proxy routing; launch the NJTech browser with no proxy. |
| CARSI institution search cannot find 南京工业大学 | Search `nanjing tech`; Elsevier may rank unrelated names when searching Chinese text. |
| WebVPN opens ScienceDirect but PDF shows CPE00001 | Use CARSI instead of repeatedly retrying WebVPN. |
| `requests` returns 403/CPE/challenge HTML for a ScienceDirect asset | Use Camofox page-context fetch from the loaded PDF viewer. |
| Turnstile/Cloudflare appears | Wait for the user to complete it manually in the visible browser, then retry page-context fetch. |
| PDF viewer opens but no file lands on disk | Use page-context fetch first; browser download button automation is only a fallback. |

## Regression Examples

- `10.1016/j.engfailanal.2025.110281`: verified as an 18-page `%PDF-1.7` file via CARSI-Camofox.
- `10.1016/j.engstruct.2021.112190`: verified as an 11-page `%PDF-1.7` file via CARSI-Camofox.
- `10.1016/j.conbuildmat.2026.145699`, PII `S0950061826006008`: use only as a legal NJTech/CARSI/ScienceDirect access test case; do not store the PDF or signed links in the repository.
