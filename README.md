# njtech-paper

`njtech-paper` is a Codex skill for helping Nanjing Tech University users legally download and troubleshoot institutional-access academic PDFs. It focuses on `scansci-pdf`, NJTech WebVPN, CARSI/OpenAthens, ScienceDirect, Camofox, proxy conflicts, missing installs, and Cloudflare/CPE failure modes.

This repository contains process guidance for an AI coding agent. It does not contain credentials, cookies, WebVPN tokens, Cloudflare clearance values, signed PDF links, browser profiles, or paper PDFs.

## Quick Start

Install the skill:

```powershell
git clone https://github.com/fffaang/njtech-paper.git "$env:USERPROFILE\.codex\skills\njtech-paper"
```

On Unix-like systems:

```bash
git clone https://github.com/fffaang/njtech-paper.git ~/.codex/skills/njtech-paper
```

Then use the agent auto setup path. This lets Codex handle installing scansci-pdf if missing, NJTech legal-only config, and dependency checks:

```text
Use $njtech-paper to set up this computer for NJTech legal paper access, installing scansci-pdf if missing, then download https://doi.org/...
```

Manual one-command setup is also available:

```powershell
python scripts/bootstrap_njtech_paper.py
```

On Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_njtech_paper.ps1
```

The older manual install command still works when you need to repair a Python environment directly:

```powershell
python -m pip install --upgrade pip
python -m pip install "scansci-pdf[cloakbrowser,vpnsci]" pypdf
```

Verify it is available:

```powershell
scansci-pdf check
scansci-pdf --help
```

Then invoke the skill in Codex:

```text
Use $njtech-paper to download https://doi.org/... through NJTech institutional access and verify the PDF.
```

The user logs in manually on the official 南京工业大学 CAS/WebVPN/CARSI page when the browser opens. The agent should not ask for or store credentials.

## Zero-Friction Setup

Most users should not need to understand `pip`, extras, or config files. The skill should run `scripts/bootstrap_njtech_paper.py` automatically when `scansci-pdf` is missing or incomplete.

The bootstrap script:

- Checks Python 3.11+.
- Installs or repairs `scansci-pdf[cloakbrowser,vpnsci]` and `pypdf`.
- Runs `scansci-pdf check`.
- Merges NJTech `legal_only` config into `~/.scansci-pdf/config.json`.
- Does not save your password, does not ask for NJTech credentials, and does not enable Sci-Hub, LibGen, or Tor.

Preview the actions without changing anything:

```powershell
python scripts/bootstrap_njtech_paper.py --dry-run
```

## Local Private Session Reuse

`njtech-paper` should aim for one-time local login on the same computer: first login, then reuse local session if valid. This does not save your password. It only reuses official session material already issued to this system user on this computer.

The local cache is private to your machine:

- Windows: `%USERPROFILE%\.scansci-pdf\cache`
- Unix-like systems: `~/.scansci-pdf/cache`

The cache may include browser profile data, CARSI cookies, publisher cookies, WebVPN cookies, and related session files. These files help avoid typing your NJTech account password every time, but they are still sensitive login state: do not share or commit cache, do not sync it to a public/cloud repository, and do not copy it to another person's computer.

The session may expire when NJTech, CARSI, the publisher, MFA, or Cloudflare/Turnstile requires a fresh check. In that case, the agent should reopen the official browser login flow and wait while you log in manually.

For NJTech WebVPN warm-up, this command can create local WebVPN cookies:

```powershell
scansci-pdf login --login-type webvpn
```

For ScienceDirect/CARSI, warm up by running a normal legal DOI download once. The first successful browser login/download saves local CARSI/publisher cookies and persistent Camofox profile data for later reuse. Do not use `scansci-pdf login --login-type carsi` as a recommended command because the current CLI does not implement that branch.

## When To Use

Use this skill when:

- A user has their own valid NJTech account and wants to access a paper through institutional access.
- `scansci-pdf` is missing, not on `PATH`, or not configured for NJTech.
- ScienceDirect/CARSI/OpenAthens cannot find 南京工业大学 unless searching `nanjing tech`.
- NJTech WebVPN opens, but ScienceDirect returns CPE00001.
- A browser can display a ScienceDirect PDF, but normal HTTP requests return 403, CPE, or challenge HTML.
- Codex needs a proxy to work, while NJTech login or Camofox must bypass that proxy.

Do not use this skill for Sci-Hub, LibGen, Tor, leaked links, shared accounts, shared cookies, or non-institutional access routes.

## Example Prompts

First-time setup plus download:

```text
Use $njtech-paper to install/check scansci-pdf, configure NJTech legal-only access, then download https://doi.org/10.1016/j.conbuildmat.2026.145699.
```

Auto setup plus download:

```text
Use $njtech-paper to set up this computer for NJTech legal paper access, installing scansci-pdf if missing, then download https://doi.org/...
```

Normal DOI download:

```text
Use $njtech-paper to download https://doi.org/10.1016/j.engstruct.2021.112190 through NJTech institutional access and verify the PDF.
```

Proxy conflict:

```text
Use $njtech-paper. Codex needs iKuuu/proxy, but NJTech login fails with proxy. Keep Codex working and launch Camofox with no proxy.
```

CARSI institution search:

```text
Use $njtech-paper. CARSI cannot find 南京工业大学; try the Elsevier/OpenAthens search term nanjing tech.
```

Already at a ScienceDirect PDF viewer:

```text
Use $njtech-paper. The browser is already on the ScienceDirect PDF viewer; save the PDF with page-context fetch and verify it.
```

Warm up local session reuse:

```text
Use $njtech-paper to warm up my local NJTech/CARSI session on this computer, then download https://doi.org/...
```

Reuse an existing local session:

```text
Use $njtech-paper to reuse my existing local NJTech session if valid; only open login if the session expired.
```

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

ScienceDirect may reject ordinary HTTP clients even after browser login. A `requests` call with cookies can still receive 403, CPE, or Cloudflare challenge HTML.

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

The agent should base64-encode the bytes inside `page.evaluate`, decode them in Python, write the file only if it starts with `%PDF-`, then verify the PDF.

## Troubleshooting

| Symptom | What to do |
|---|---|
| `scansci-pdf not installed`, `command not found`, or `ModuleNotFoundError: scansci_pdf` | Run `python scripts/bootstrap_njtech_paper.py` first. If the bootstrap script is unavailable, run `python -m pip install "scansci-pdf[cloakbrowser,vpnsci]" pypdf`, then `scansci-pdf check`. |
| `ModuleNotFoundError: bs4`, missing `beautifulsoup4`, or `No module named 'cloakbrowser'` | Run `python -m pip install --upgrade "scansci-pdf[cloakbrowser,vpnsci]" pypdf`; install into the same Python environment that runs `scansci-pdf`, then run `scansci-pdf check`. |
| Install succeeds but `scansci-pdf` is not recognized | Activate the same virtual environment, use the matching Python, or reopen the terminal. |
| The user is asked to log in every time | Confirm the same system user, Python environment, and `cache_dir` are being used; check whether cache was cleared or the session expired. |
| NJTech WebVPN shows `ERR_CONNECTION_CLOSED` | Keep the proxy if Codex needs it, but launch Camofox/Chrome with `camofox_no_proxy=true` or `--no-proxy-server`. |
| CARSI cannot find 南京工业大学 | Search `nanjing tech`. |
| ScienceDirect through WebVPN returns CPE00001 | Use CARSI/OpenAthens instead of repeatedly retrying WebVPN. |
| ScienceDirect asset returns 403/CPE/challenge HTML | Use page-context fetch from the loaded Camofox PDF viewer. |
| Cloudflare/Turnstile appears | The user completes verification manually in the visible browser; the agent retries only after that. |

## Credential Safety

- Each user needs their own valid NJTech institutional account and permission to access the requested publisher resource.
- Do not configure one person's NJTech account for everyone.
- Do not paste, upload, print, export, or share account names, passwords, cookies, WebVPN tokens, verification codes, Cloudflare clearance values, browser profiles, storage state, or session files in chat or GitHub.
- It is okay for your own computer to keep a private local session cache for reuse. Do not share or commit cache, browser profiles, login state, downloaded paper PDFs, signed ScienceDirect asset URLs, or private access artifacts to GitHub.
- Credentials stay between the user and the official NJTech/CARSI/WebVPN login page.

## FAQ

### Can I configure one NJTech account for everyone?

No. Each user must log in with their own authorized NJTech account on the official NJTech/CARSI/WebVPN page. Hiding the password in a script, config, server, encrypted file, browser profile, cookie jar, or token store is still shared-account access and should be refused.

### Does the agent need my password?

No. The agent should open or guide the official browser flow only. Type your account, password, MFA, or verification code directly into the official page, not into chat or configuration files.

### Why does this still need a local install?

`scansci-pdf` controls the browser, legal-only config, local cache, and PDF verification on the user's computer. The skill is guidance and automation glue; it should not bundle a stale copy of `scansci-pdf` or run downloads through someone else's machine.

### What does bootstrap do?

It installs or repairs the local `scansci-pdf[cloakbrowser,vpnsci]` environment, sets NJTech `legal_only` config, and runs dependency checks. It does not ask for or save your NJTech password, and it does not enable Sci-Hub, LibGen, or Tor.

### Why not bundle scansci-pdf inside this skill?

Bundling would become stale quickly and make dependency/security fixes harder. The bootstrap script keeps the install local and upgradable while hiding most of the setup friction.

### Why can one computer usually avoid repeated logins?

After the first official login, `scansci-pdf` can reuse local session if valid by reading private cache/profile/cookie files on the same computer. This local tool access is different from sending cookies to an agent or another person. It does not save your password, and it only works until the official session may expire.

### Can I guarantee I will never need to log in again?

No. NJTech, CARSI, publishers, MFA, or Cloudflare/Turnstile can expire or reject a session at any time. When that happens, the agent should open the official page and wait while you log in manually again.

### What should I do on a public computer or when switching accounts?

Clear the local session cache before reuse. Remove the relevant files under `%USERPROFILE%\.scansci-pdf\cache` or `~/.scansci-pdf/cache`, especially publisher profiles, `carsi_cookies`, `publisher_cookies.*`, `vpnsci-cookies.*`, and `browser_state.json`.

### Can I copy my cache to someone else so they do not need to log in?

No. Local cache contains sensitive login state. Copying browser profiles, cookies, storage state, or WebVPN/CARSI session files to others is equivalent to sharing your account/session and should be refused.

### Can I upload downloaded PDFs to this repository?

No. Do not upload paper PDFs, signed URLs, cookies, storage state, browser profiles, logs containing private URLs, or any other access artifacts.

### What if my session expires?

Run the skill again. The agent should reopen the official login flow and wait while you manually authenticate.

## Verification Checklist

Before reporting success, verify:

- The file exists and is larger than 5 KB.
- The first bytes are `%PDF-`.
- The file ends with `%%EOF`.
- `pypdf` can read the page count.
- Extracted text contains the expected title fragment, journal name, DOI fragment, or another reliable bibliographic marker.

Tested ScienceDirect examples:

- `10.1016/j.engfailanal.2025.110281`: downloaded as an 18-page `%PDF-1.7` file via CARSI-Camofox.
- `10.1016/j.engstruct.2021.112190`: downloaded as an 11-page `%PDF-1.7` file via CARSI-Camofox.
- `10.1016/j.conbuildmat.2026.145699`, PII `S0950061826006008`: first-time setup test case for legal NJTech/CARSI/ScienceDirect access only.

## Maintainer Checks

Before publishing changes, run:

```powershell
python scripts/validate_docs.py
```

The validator checks required documentation phrases, skill frontmatter, and common accidental secret patterns.

## Repository Contents

```text
.
├── README.md
├── SKILL.md
├── SECURITY.md
├── agents/
│   └── openai.yaml
└── scripts/
    ├── bootstrap_njtech_paper.py
    ├── install_njtech_paper.ps1
    └── validate_docs.py
```

`SKILL.md` is the actual Codex skill. `agents/openai.yaml` provides UI metadata for Codex.
