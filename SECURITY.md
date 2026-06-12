# Security Policy

`njtech-paper` is a process skill for legal NJTech institutional access. It must not become a credential-sharing, account-proxying, or paper-redistribution tool.

## Do Not Commit

Do not commit or publish:

- NJTech account names, passwords, MFA codes, verification codes, or recovery details.
- Cookies, tokens, WebVPN tokens, Cloudflare clearance values, browser profiles, session files, storage state, or HAR captures.
- signed ScienceDirect asset URLs, private redirected URLs, or logs that contain access-bearing query strings or headers.
- Downloaded paper PDFs or publisher-provided files that are not meant to be redistributed.
- Local config backups that contain private paths, accounts, cookies, tokens, or proxy credentials.

## Account Sharing

Do not configure one person's NJTech account for everyone. Hidden credentials in scripts, encrypted files, browser profiles, cookie jars, servers, or proxy services still count as shared-account access. Each user must authenticate manually with their own authorized account on the official NJTech/CARSI/WebVPN page.

## If Something Leaks

1. Stop using the leaked session or artifact immediately.
2. Remove the leaked file or text from the repository and any release artifacts.
3. Clear browser sessions, revoke or rotate affected credentials if possible, and change the password when an account secret was exposed.
4. Treat leaked cookies, tokens, storage state, and Cloudflare clearance values as sensitive even if no password was exposed.
5. Do not open a public issue that contains the secret; describe the problem without pasting private values.

## Legal Access Boundary

This project documents legal institutional-access workflows only. Do not add Sci-Hub, LibGen, Tor, leaked links, shared cookies, shared accounts, or代下 workflows.
