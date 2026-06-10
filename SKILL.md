---
name: njtech-paper
description: Use when helping Nanjing Tech University users legally download or troubleshoot institutional-access academic PDFs through scansci-pdf, NJTech WebVPN, CARSI/OpenAthens, ScienceDirect, or Camofox.
---

# NJTech Paper

## Core Rule

Use only legal institutional access. Do not use Sci-Hub, LibGen, Tor, leaked links, shared cookies, saved passwords, WebVPN tokens, or Cloudflare clearance values. If authentication or a human verification page appears, ask the user to complete it in the browser.

## Known Good Configuration

For NJTech access through `scansci-pdf`, prefer:

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

When CARSI/OpenAthens asks for an institution, search for `nanjing tech`, then select 南京工业大学 / Nanjing Tech University.

## Download Workflow

1. Confirm `scansci-pdf` is installed and points to the intended local source/MCP config.
2. Confirm global config is legal-only and NJTech-specific; never enable illicit sources to solve access trouble.
3. For ScienceDirect, try CARSI first. Use NJTech WebVPN as a fallback, but if ScienceDirect returns CPE00001 through WebVPN, switch back to CARSI instead of looping.
4. If iKuuu or another proxy is required for Codex but blocks NJTech login, keep the proxy running for Codex and launch Camofox/Chrome with no proxy (`camofox_no_proxy=true` or `--no-proxy-server`).
5. Let the user complete NJTech CAS, CARSI, and any Cloudflare/Turnstile verification in the visible Camofox window.
6. Once the browser reaches a `pdf.sciencedirectassets.com/.../main.pdf` PDF viewer, fetch the PDF from inside that same browser page context.
7. Save the bytes, then verify the file before claiming success.

## ScienceDirect Asset Fetch Pattern

Ordinary `requests` can still return 403, CPE, or challenge HTML even with browser cookies. The reliable path is page-context fetch after the PDF viewer is open and the challenge is solved:

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

In Python/Playwright, base64-encode the bytes in `page.evaluate`, decode them in Python, and write only when the content starts with `%PDF-`.

## Troubleshooting

| Symptom | Action |
|---|---|
| Chrome shows `ERR_CONNECTION_CLOSED` for NJTech WebVPN | Check proxy routing. Keep iKuuu on if Codex needs it, but launch the browser used for NJTech with no proxy. |
| CARSI institution search cannot find 南京工业大学 | Search `nanjing tech`; Elsevier may rank unrelated Chinese/Japanese names when searching the Chinese name. |
| WebVPN opens ScienceDirect but PDF shows CPE00001 | Treat WebVPN as unsuitable for that publisher/session and use CARSI. |
| `requests` returns 403/CPE/challenge HTML for a ScienceDirect asset | Do not keep adding cookies. Use Camofox page-context fetch from the loaded PDF viewer. |
| Turnstile/Cloudflare appears | Wait for the user to complete it manually in the visible browser, then retry page-context fetch. |
| PDF viewer opens but no file lands on disk | Use page-context fetch first; browser download button automation is a fallback. |

## Verification

Before reporting success, run a file-level check:

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

Known regression example: DOI `10.1016/j.engfailanal.2025.110281` should save an 18-page `%PDF-1.7` file whose text includes `Failure modes analysis of reinforced concrete beams under impact loads based on machine learning and SHAP approach`.
