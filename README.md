# njtech-paper

`njtech-paper` is a Codex skill for helping Nanjing Tech University users legally download and troubleshoot institutional-access academic PDFs. It focuses on `scansci-pdf`, NJTech WebVPN, CARSI/OpenAthens, ScienceDirect, Camofox, proxy conflicts, and Cloudflare/CPE failure modes.

This repository contains process guidance for an AI coding agent. It does not contain credentials, cookies, WebVPN tokens, Cloudflare clearance values, signed PDF links, or any paper PDFs.

## When To Use

Use this skill when:

- A user has a valid NJTech account and wants to download a paper through institutional access.
- ScienceDirect/CARSI/OpenAthens cannot find 南京工业大学 unless searching `nanjing tech`.
- NJTech WebVPN opens, but ScienceDirect returns CPE00001.
- A browser can display a ScienceDirect PDF, but normal HTTP requests return 403, CPE, or challenge HTML.
- Codex needs a proxy to work, while NJTech login or Camofox must bypass that proxy.

Do not use this skill to access papers through Sci-Hub, LibGen, Tor, leaked links, shared cookies, or other non-institutional routes.

## Installation

Clone or copy this repository into the Codex skills directory:

```powershell
git clone https://github.com/fffaang/njtech-paper.git "$env:USERPROFILE\.codex\skills\njtech-paper"
```

On Unix-like systems, use:

```bash
git clone https://github.com/fffaang/njtech-paper.git ~/.codex/skills/njtech-paper
```

Then invoke it in Codex with:

```text
Use $njtech-paper to download this DOI through NJTech institutional access and verify the PDF.
```

## Prerequisites

- Python 3.11 or newer.
- A valid 南京工业大学 institutional account.
- A visible browser session for NJTech CAS, WebVPN, CARSI, and possible human verification.
- `scansci-pdf` with the Camofox and WebVPN dependencies installed.

If `scansci-pdf` is not installed, or an agent reports `scansci-pdf not installed`, install it before asking the skill to download a DOI:

```powershell
python -m pip install --upgrade pip
python -m pip install "scansci-pdf[cloakbrowser,vpnsci]" pypdf
```

Then verify the command is available:

```powershell
scansci-pdf check
scansci-pdf --help
```

If `python -m pip install ...` succeeds but `scansci-pdf` is still not recognized, activate the same virtual environment used for installation, reopen the terminal, or run the command through that Python environment.

## Usage

1. Install the skill into `~/.codex/skills/njtech-paper` on Unix-like systems, or `%USERPROFILE%\.codex\skills\njtech-paper` on Windows.
2. Install and configure `scansci-pdf` for legal-only NJTech access. Use `download_strategy=legal_only`, NJTech WebVPN/CARSI settings, and `camofox_no_proxy=true`.
3. Ask Codex to use the skill with a DOI:

```text
Use $njtech-paper to download https://doi.org/... through NJTech institutional access and verify the PDF.
```

4. On first use, or after the school session expires, Codex will open a visible Camofox browser. The user must log in manually on the official 南京工业大学 CAS, WebVPN, or CARSI page with their own NJTech account.
5. If Cloudflare/Turnstile or another human verification page appears, the user must complete it manually in that browser window.
6. After the browser reaches the publisher PDF viewer, the agent should save the PDF and verify `%PDF-`, page count, and title/DOI text before reporting success.

## First-time Setup

For a first-time user, ask the agent to do setup before downloading:

```text
Use $njtech-paper to install/check scansci-pdf, configure NJTech legal-only access, then download https://doi.org/10.1016/j.conbuildmat.2026.145699.
```

The agent should:

1. Check whether `scansci-pdf` exists.
2. If missing, install `scansci-pdf[cloakbrowser,vpnsci]` and `pypdf`.
3. Set or confirm NJTech legal-only access settings.
4. Open the official login flow only when needed; the user enters credentials manually.
5. Download and verify the PDF.

## Credential Safety

- Users need their own valid NJTech institutional account and permission to access the requested publisher resource.
- Do not send account names, passwords, cookies, WebVPN tokens, verification codes, Cloudflare clearance values, or browser session files to the agent.
- Do not commit browser profiles, login state, downloaded paper PDFs, signed ScienceDirect asset URLs, or any other private access artifacts to GitHub.
- The skill should guide the browser workflow only; credentials stay between the user and the official NJTech/CARSI/WebVPN login page.

## Recommended scansci-pdf Configuration

The skill assumes legal-only institutional access:

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

For Elsevier/CARSI institution search, use `nanjing tech` and select 南京工业大学 / Nanjing Tech University.

## Key Download Pattern

The most important lesson from testing is that ScienceDirect may reject ordinary HTTP clients even after browser login. A `requests` call with cookies can still receive 403, CPE, or Cloudflare challenge HTML.

When the Camofox browser reaches a `pdf.sciencedirectassets.com/.../main.pdf` PDF viewer, fetch the PDF from inside that same page context:

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

The agent should base64-encode the bytes inside `page.evaluate`, decode them in Python, write the file only if it starts with `%PDF-`, then verify the resulting PDF.

## Verification Checklist

Before reporting success, verify:

- The file exists and is larger than 5 KB.
- The first bytes are `%PDF-`.
- The file ends with `%%EOF`.
- `pypdf` can read the page count.
- Extracted text contains the expected title fragment, journal name, DOI fragment, or another reliable bibliographic marker.

Two tested ScienceDirect examples:

- `10.1016/j.engfailanal.2025.110281`: downloaded as an 18-page `%PDF-1.7` file via CARSI-Camofox.
- `10.1016/j.engstruct.2021.112190`: downloaded as an 11-page `%PDF-1.7` file via CARSI-Camofox.

Additional first-time setup test case from a user report:

- DOI: `10.1016/j.conbuildmat.2026.145699`
- ScienceDirect PII: `S0950061826006008`
- Expected path: legal NJTech/CARSI/ScienceDirect access only; do not include PDFs or signed asset links in the repository.

## Repository Contents

```text
.
├── README.md
├── SKILL.md
└── agents/
    └── openai.yaml
```

`SKILL.md` is the actual Codex skill. `agents/openai.yaml` provides UI metadata for Codex.
