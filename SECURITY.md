# Security Policy

`njtech-paper` is a process skill for legal NJTech institutional access. It must not become a credential-sharing, account-proxying, session-sharing, or paper-redistribution tool.

## Local Private Session Reuse

Local private session reuse is allowed for the same authorized user on the same computer. It can reuse local browser profiles, CARSI cookies, publisher cookies, WebVPN cookies, and storage state while the official session remains valid. It does not save your password.

Local session reuse is still sensitive: reuse local session if valid, but do not share or commit cache, paste it into chat, copy it to another person, upload it to GitHub, sync it to a public/cloud folder, place it inside the skill, or use it for代下 service. Local tools may read private cache on the same computer; agents and other users should not receive those values. The session may expire whenever NJTech, CARSI, a publisher, MFA, or Cloudflare/Turnstile requires fresh authentication.

## Do Not Commit

Do not commit or publish:

- NJTech account names, passwords, MFA codes, verification codes, or recovery details.
- Cookies, tokens, WebVPN tokens, Cloudflare clearance values, browser profiles, session files, storage state, or HAR captures.
- signed ScienceDirect asset URLs, private redirected URLs, or logs that contain access-bearing query strings or headers.
- Downloaded paper PDFs or publisher-provided files that are not meant to be redistributed.
- Local config backups that contain private paths, accounts, cookies, tokens, or proxy credentials.

Vendored release artifacts are allowed only when they contain code, such as a patched `scansci-pdf` wheel. Do not place browser profiles, cache directories, cookies, tokens, storage state, downloaded PDFs, signed links, logs with private headers, or account material inside `vendor/`, GitHub releases, or the skill directory.

## Account Sharing

Do not configure one person's NJTech account for everyone. Hidden credentials in scripts, encrypted files, browser profiles, cookie jars, servers, or proxy services still count as shared-account access. Each user must authenticate manually with their own authorized account on the official NJTech/CARSI/WebVPN page. A private cache for one user on one computer is acceptable; copying that cache to others is not.

## If Something Leaks

1. Stop using the leaked session or artifact immediately.
2. Remove the leaked file or text from the repository and any release artifacts.
3. Clear browser sessions, revoke or rotate affected credentials if possible, and change the password when an account secret was exposed.
4. Treat leaked cookies, tokens, storage state, and Cloudflare clearance values as sensitive even if no password was exposed.
5. Do not open a public issue that contains the secret; describe the problem without pasting private values.

## Legal Access Boundary

This project documents legal institutional-access workflows only. Do not add Sci-Hub, LibGen, Tor, leaked links, shared cookies, shared accounts, or代下 workflows.

Cloudflare/Turnstile or ScienceDirect `manual_verification_required` states must be handled only by waiting for the authorized user in the visible official browser page. Do not bypass, script around, submit, store, or share verification answers, challenge HTML, clearance values, cookies, or signed asset URLs.
