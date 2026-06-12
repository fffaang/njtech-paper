"""CARSI (Shibboleth/SAML) federated authentication for publisher access.

Provides institutional login through CARSI federation, supporting
publishers like Elsevier, Springer Nature, Wiley, ACS, etc.
"""

from __future__ import annotations

import base64
import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from ..config import DATA_DIR
from ..log import get_logger
from ..publisher_strategies import (
    _AUTH_KEYWORDS,
    _AUTH_TITLES,
    _COOKIE_CONSENT_DISMISS_JS,
    _SSO_LINK_FINDER_JS,
    _INSTITUTION_CLICK_JS,
    _institution_search_terms,
)

log = get_logger()

_PUBLISHER_CONFIGS_FILE = DATA_DIR / "publisher_carsi.json"
_PKG_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_PKG_PUBLISHER_CONFIGS_FILE = _PKG_DATA_DIR / "publisher_carsi.json"


@dataclass
class PublisherCARSIConfig:
    name: str
    domains: list[str]
    login_url: str
    search_selector: str
    result_selector: str
    success_url_pattern: str
    pdf_pattern: str


def _load_publisher_configs() -> dict[str, PublisherCARSIConfig]:
    # Try package data first, then user data dir
    config_file = _PKG_PUBLISHER_CONFIGS_FILE if _PKG_PUBLISHER_CONFIGS_FILE.exists() else _PUBLISHER_CONFIGS_FILE
    if not config_file.exists():
        return {}
    data = json.loads(config_file.read_text(encoding="utf-8"))
    configs = {}
    for key, val in data.items():
        configs[key] = PublisherCARSIConfig(**val)
    return configs


def detect_publisher(url: str) -> str | None:
    """Detect publisher key from a URL."""
    hostname = urlparse(url).hostname or ""
    configs = _load_publisher_configs()
    for key, cfg in configs.items():
        for domain in cfg.domains:
            if domain in hostname:
                return key
    return None


def _publisher_selector_name(publisher: str) -> str:
    """Map CARSI publisher keys to publisher strategy selector names."""
    return "Elsevier" if publisher == "sciencedirect" else publisher


def _find_accessible_pdf_link(html: str, article_url: str, publisher: str) -> str | None:
    """Find a publisher-specific PDF link that proves the article page is accessible."""
    from ..publisher_strategies import _extract_pdf_from_page
    return _extract_pdf_from_page(html, article_url, _publisher_selector_name(publisher))


def _extract_sciencedirect_pii(*values: str) -> str:
    """Extract a ScienceDirect PII from article URLs, redirect URLs, or HTML."""
    import re
    for value in values:
        if not value:
            continue
        match = re.search(r"(?:retrieve/)?pii/([A-Z0-9]+)", value, re.IGNORECASE)
        if match:
            return match.group(1)
        match = re.search(r"\b(S[0-9A-Z]{16,})\b", value, re.IGNORECASE)
        if match:
            return match.group(1)
    return ""


class CARSIClient:
    """Manages CARSI/Shibboleth federated authentication with academic publishers."""

    _login_lock = threading.Lock()

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self._sessions: dict[str, requests.Session] = {}
        self._publisher_configs = _load_publisher_configs()
        self._cookie_dir = Path(config.get("cache_dir", str(DATA_DIR / "cache"))) / "carsi_cookies"
        self._cookie_dir.mkdir(parents=True, exist_ok=True)

    def _cookie_path(self, publisher: str) -> Path:
        return self._cookie_dir / f"{publisher}.json"

    def _get_session(self, publisher: str) -> requests.Session:
        if publisher not in self._sessions:
            sess = requests.Session()
            sess.trust_env = False
            sess.headers.update({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            })
            self._sessions[publisher] = sess
        return self._sessions[publisher]

    def login(self, publisher: str, force: bool = False) -> bool:
        """Ensure we have a valid CARSI session for the given publisher."""
        with self._login_lock:
            if not force and self._try_load_cookies(publisher):
                log.info(f"   [CARSI] Loaded saved cookies for {publisher}")
                return True
            log.info(f"   [CARSI] No valid session for {publisher}. Opening browser...")
            return self._browser_login(publisher)

    def fetch(self, url: str, **kwargs) -> requests.Response | None:
        """Fetch a URL using CARSI-authenticated session."""
        publisher = detect_publisher(url)
        if not publisher:
            return None

        if not self.login(publisher):
            return None

        sess = self._get_session(publisher)
        kwargs.setdefault("timeout", 30)
        kwargs.setdefault("allow_redirects", True)
        try:
            return sess.get(url, **kwargs)
        except requests.RequestException as e:
            log.warning(f"   [CARSI] Fetch failed: {e}")
            return None

    def download_via_camofox(self, doi: str, article_url: str, output_path: Path) -> dict[str, Any] | None:
        """Download PDF via stealth browser browser with CARSI auth. Single session: login + download."""
        publisher = detect_publisher(article_url)
        if not publisher:
            return None
        cfg = self._publisher_configs.get(publisher)
        if not cfg:
            return None

        try:
            from cloakbrowser import launch  # noqa: F401
        except ImportError:
            log.info("   [CARSI-Camofox] cloakbrowser not installed")
            return None

        idp_name = self.config.get("carsi_idp_name", "")
        if not idp_name:
            log.info("   [CARSI-Camofox] No carsi_idp_name configured")
            return None

        institution_terms = _institution_search_terms(idp_name) or [idp_name]

        from ..pdf_utils import is_pdf_file, success as _success

        # Serialize browser opens across threads — only one browser at a time
        with self._login_lock:
            log.info(f"   [CARSI-Camofox] Opening browser for {publisher}...")
            try:
                from ..publisher_strategies import _visible_camofox, _save_all_cookie_formats

                with _visible_camofox(self.config, publisher, viewport=None) as (context, page):

                    # Restore saved cookies if any (supplements persistent profile)
                    cookie_file = self._cookie_path(publisher)
                    if cookie_file.exists():
                        try:
                            saved = json.loads(cookie_file.read_text(encoding="utf-8"))
                            pw_cookies = []
                            for c in saved:
                                pw_c = {"name": c["name"], "value": c["value"], "domain": c.get("domain", ""), "path": c.get("path", "/")}
                                if pw_c["domain"]:
                                    pw_cookies.append(pw_c)
                            if pw_cookies:
                                context.add_cookies(pw_cookies)
                                log.info(f"   [CARSI-Camofox] Restored {len(pw_cookies)} cookies from file")
                        except Exception:
                            pass

                    # Capture PDF from network
                    captured_pdf = []
                    def save_pdf_bytes(pdf_bytes: bytes, source: str) -> dict[str, Any] | None:
                        if len(pdf_bytes) <= 5000 or not pdf_bytes.startswith(b"%PDF-"):
                            return None
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        output_path.write_bytes(pdf_bytes)
                        if is_pdf_file(output_path):
                            log.info(f"   [CARSI-Camofox] PDF saved from {source}: {len(pdf_bytes)} bytes")
                            return _success(doi, output_path, "CARSI-Camofox")
                        return None

                    def on_response(response):
                        try:
                            ct = response.headers.get("content-type", "")
                            url = response.url
                            is_pdf_ct = "pdf" in ct.lower() or "octet-stream" in ct.lower()
                            lower_url = url.lower()
                            is_pdf_url = (
                                lower_url.endswith(".pdf")
                                or "/pdfdirect/" in lower_url
                                or "/doi/pdf/" in lower_url
                                or "/pdfft" in lower_url
                                or "pdf.sciencedirectassets.com" in lower_url
                            )
                            if not (is_pdf_ct or is_pdf_url):
                                return
                            if response.status >= 400:
                                return
                            body = response.body()
                            if len(body) > 5000 and body[:4] == b"%PDF-":
                                captured_pdf.append(body)
                                log.info(f"   [CARSI-Camofox] PDF captured: {len(body)} bytes")
                        except Exception:
                            pass
                    page.on("response", on_response)

                    def fetch_pdf_via_page(pdf_url: str, source: str) -> dict[str, Any] | None:
                        try:
                            result = page.evaluate(
                                """
                                async (url) => {
                                    const resp = await fetch(url, {
                                        credentials: 'include',
                                        headers: {'Accept': 'application/pdf,*/*'}
                                    });
                                    const buffer = await resp.arrayBuffer();
                                    const bytes = new Uint8Array(buffer);
                                    let binary = '';
                                    const chunk = 0x8000;
                                    for (let i = 0; i < bytes.length; i += chunk) {
                                        binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
                                    }
                                    return {
                                        status: resp.status,
                                        contentType: resp.headers.get('content-type') || '',
                                        finalUrl: resp.url,
                                        body: btoa(binary)
                                    };
                                }
                                """,
                                pdf_url,
                            )
                            body = base64.b64decode(result.get("body", ""))
                            log.info(
                                f"   [CARSI-Camofox] Page fetch {result.get('status')} "
                                f"{result.get('contentType', '')[:40]} {len(body)} bytes"
                            )
                            return save_pdf_bytes(body, source)
                        except Exception as e:
                            log.info(f"   [CARSI-Camofox] Page PDF fetch failed: {e}")
                            return None

                    def adopt_latest_page(reason: str) -> None:
                        nonlocal page
                        try:
                            pages = context.pages
                            if pages and pages[-1] is not page:
                                page = pages[-1]
                                page.on("response", on_response)
                                log.info(
                                    f"   [CARSI-Camofox] Switched to latest page after {reason}: "
                                    f"{page.title()[:40]} {page.url[:60]}"
                                )
                        except Exception:
                            pass

                    def fetch_current_pdf_asset(source: str) -> dict[str, Any] | None:
                        try:
                            current_url = page.url
                            if "pdf.sciencedirectassets.com" not in current_url.lower():
                                return None
                            saved = fetch_pdf_via_page(current_url, f"{source} via page")
                            if saved:
                                return saved
                            resp = context.request.get(current_url, headers={"Accept": "application/pdf"}, timeout=30000)
                            body = resp.body()
                            log.info(
                                f"   [CARSI-Camofox] Asset fetch {resp.status} "
                                f"{resp.headers.get('content-type', '')[:40]} {len(body)} bytes"
                            )
                            saved = save_pdf_bytes(body, source)
                            if saved:
                                return saved
                            challenge_html = body[:200000].decode("utf-8", errors="ignore").lower()
                            if (
                                "challenges.cloudflare.com" in challenge_html
                                or "turnstile" in challenge_html
                                or "craft_challenge" in challenge_html
                                or "low-bot-score" in challenge_html
                            ):
                                log.info("   [CARSI-Camofox] ScienceDirect challenge detected; waiting for manual completion")
                                for _wait in range(24):
                                    time.sleep(5)
                                    resp = context.request.get(current_url, headers={"Accept": "application/pdf"}, timeout=30000)
                                    retry_body = resp.body()
                                    saved = save_pdf_bytes(retry_body, "ScienceDirect asset after challenge")
                                    if saved:
                                        return saved
                                log.info("   [CARSI-Camofox] ScienceDirect challenge wait timed out")
                            try:
                                debug_dir = output_path.parent
                                debug_dir.mkdir(parents=True, exist_ok=True)
                                (debug_dir / "sciencedirect_asset_url.txt").write_text(current_url, encoding="utf-8")
                                (debug_dir / "sciencedirect_asset_response.html").write_bytes(body)
                            except Exception:
                                pass
                            return None
                        except Exception as e:
                            log.info(f"   [CARSI-Camofox] Asset fetch failed: {e}")
                            return None

                    def wait_for_login_if_needed(reason: str, max_wait: int = 180) -> None:
                        try:
                            url = page.url
                            title = page.title()
                        except Exception:
                            return
                        if not (any(x in url.lower() for x in _AUTH_KEYWORDS) or any(x in title for x in _AUTH_TITLES)):
                            return
                        log.info(f"   [CARSI-Camofox] Login required after {reason}. Please complete it in the browser...")
                        elapsed = 0
                        while elapsed < max_wait:
                            time.sleep(3)
                            elapsed += 3
                            try:
                                url = page.url
                                title = page.title()
                            except Exception:
                                return
                            if not (any(x in url.lower() for x in _AUTH_KEYWORDS) or any(x in title for x in _AUTH_TITLES)):
                                try:
                                    cookies = context.cookies()
                                    _save_all_cookie_formats(cookies, publisher, self.config)
                                except Exception:
                                    pass
                                return

                    def dismiss_cookie_consent(reason: str) -> None:
                        try:
                            dismissed = page.evaluate(_COOKIE_CONSENT_DISMISS_JS)
                            if dismissed:
                                log.info(
                                    f"   [CARSI-Camofox] Dismissed cookie banner after {reason}: "
                                    f"{str(dismissed)[:120]}"
                                )
                                time.sleep(1)
                        except Exception as e:
                            log.info(f"   [CARSI-Camofox] Cookie banner check failed after {reason}: {e}")

                    def select_institution_if_present(reason: str) -> bool:
                        dismiss_cookie_consent(reason)
                        try:
                            result = page.evaluate(_INSTITUTION_CLICK_JS, institution_terms)
                        except Exception as e:
                            log.info(f"   [CARSI-Camofox] Institution select script failed after {reason}: {e}")
                            return False

                        if not isinstance(result, dict):
                            result = {"status": "legacy", "text": str(result or "")}
                        status = result.get("status")
                        candidates = result.get("candidates") or []
                        log.info(
                            f"   [CARSI-Camofox] Institution select after {reason}: "
                            f"status={status} term={result.get('matchedTerm', '')!r} "
                            f"text={str(result.get('text', ''))[:80]!r}"
                        )
                        if status == "no_input":
                            log.info(
                                f"   [CARSI-Camofox] No institution search input after {reason}; "
                                f"url={page.url[:100]} title={page.title()[:80]} candidates={str(candidates)[:180]}"
                            )
                            return False

                        time.sleep(4)
                        adopt_latest_page(reason)
                        try:
                            if any(x in page.url.lower() for x in _AUTH_KEYWORDS):
                                return True
                        except Exception:
                            pass
                        page.evaluate("""
                            () => {
                                const labels = ['continue', 'next', 'select', 'submit',
                                                '提交', '继续', '下一步', '选择'];
                                const buttons = [...document.querySelectorAll('button, a, input[type="submit"]')];
                                const target = buttons.find((el) => {
                                    const text = ((el.innerText || el.value || el.textContent || '')).trim().toLowerCase();
                                    return text && labels.some((label) => text.includes(label));
                                });
                                if (target) target.click();
                                return !!target;
                            }
                        """)
                        time.sleep(5)
                        adopt_latest_page(reason)
                        try:
                            still_wayf = any(x in page.url.lower() for x in ("wayf", "institution"))
                            if still_wayf:
                                log.info(
                                    f"   [CARSI-Camofox] Still on institution page after {reason}: "
                                    f"url={page.url[:100]} title={page.title()[:80]} candidates={str(candidates)[:180]}"
                                )
                        except Exception:
                            pass
                        return True

                    # Step 1: Navigate to article page first (gets Cloudflare clearance)
                    log.info(f"   [CARSI-Camofox] Loading article: {article_url[:60]}")
                    try:
                        page.goto(article_url, wait_until="domcontentloaded", timeout=60000)
                        time.sleep(5)
                        dismiss_cookie_consent("article load")
                    except Exception:
                        pass

                    title = page.title()
                    url = page.url
                    log.info(f"   [CARSI-Camofox] Page: '{title[:40]}' {url[:60]}")

                    # Wait for Cloudflare challenge to resolve (visible stealth browser can pass it)
                    for _cf_wait in range(6):
                        _cf_title = (page.title() or "").lower()
                        if any(_sig in _cf_title for _sig in ("just a moment", "attention required", "verify", "security check")):
                            log.info(f"   [CARSI-Camofox] Cloudflare challenge detected, waiting... ({_cf_wait+1}/6)")
                            time.sleep(5)
                        else:
                            break
                    else:
                        log.info("   [CARSI-Camofox] Cloudflare challenge did not resolve")

                    # Step 1b: Check if restored cookies already grant access
                    has_cookies = cookie_file.exists()
                    needs_login = False
                    try:
                        needs_login = page.evaluate("""
                            () => {
                                if (!document.body) return true;
                                const body = (document.body.innerText || '').toLowerCase();
                                const hasPaywall = body.includes('purchase') || body.includes('subscribe')
                                    || body.includes('access through your institution')
                                    || body.includes('sign in to access')
                                    || body.includes('buy this article');
                                const hasPdf = !!document.querySelector('a[href*="pdf"], a[href*="download"], iframe[src*="pdf"]');
                                return hasPaywall && !hasPdf;
                            }
                        """)
                    except Exception as _e:
                        log.info(f"   [CARSI-Camofox] paywall check error (likely Cloudflare): {_e}")
                        needs_login = True

                    # Even if page looks accessible, verify cookies work by
                    # trying a quick pdfft probe. ScienceDirect may accept
                    # expired cookies without showing a paywall, but return
                    # HTML instead of PDF for /pdfft requests.
                    cookies_valid = False
                    if has_cookies and not needs_login:
                        accessible_pdf_url = _find_accessible_pdf_link(page.content(), page.url, publisher)
                        if accessible_pdf_url:
                            cookies_valid = True
                            log.info("   [CARSI-Camofox] PDF link visible, skipping login")
                        pii_from_url = ""
                        import re as _re
                        _pm = _re.search(r"pii/([A-Z0-9]+)", page.url)
                        if _pm:
                            pii_from_url = _pm.group(1)
                        if pii_from_url and not cookies_valid:
                            try:
                                probe_ok = page.evaluate(f"""
                                    (async () => {{
                                        try {{
                                            const r = await fetch('/science/article/pii/{pii_from_url}/pdfft',
                                                {{credentials: 'include', headers: {{'Accept': 'application/pdf'}}}});
                                            const ct = r.headers.get('content-type') || '';
                                            return r.ok && ct.includes('pdf');
                                        }} catch(e) {{ return false; }}
                                    }})()
                                """)
                                cookies_valid = bool(probe_ok)
                                if cookies_valid:
                                    log.info("   [CARSI-Camofox] Cookie probe OK, skipping login")
                                else:
                                    log.info("   [CARSI-Camofox] Cookie probe failed, re-login needed")
                            except Exception:
                                log.info("   [CARSI-Camofox] Cookie probe error, will re-login")

                        if not cookies_valid and not needs_login:
                            try:
                                body_text = page.evaluate("() => document.body ? document.body.innerText : ''")
                                lowered = (body_text or "").lower()
                                article_accessible = (
                                    bool(_extract_sciencedirect_pii(page.url, article_url, page.content()))
                                    and not any(term in lowered for term in (
                                        "purchase",
                                        "subscribe",
                                        "access through your institution",
                                        "sign in to access",
                                        "buy this article",
                                        "are you a robot",
                                        "captcha",
                                    ))
                                )
                                if article_accessible:
                                    cookies_valid = True
                                    log.info("   [CARSI-Camofox] Article page accessible, skipping re-login")
                            except Exception:
                                pass

                    if not cookies_valid:
                        # Step 2: Click "Institutional login" link on article page
                        sso_clicked = page.evaluate(_SSO_LINK_FINDER_JS)
                        if not sso_clicked:
                            log.info("   [CARSI-Camofox] No SSO link found, trying direct login URL...")
                            page.goto(cfg.login_url, wait_until="domcontentloaded", timeout=30000)
                            time.sleep(5)
                            dismiss_cookie_consent("direct login URL")
                            adopt_latest_page("direct login URL")

                        time.sleep(8)
                        dismiss_cookie_consent("institutional login")

                        # Step 3: Search for institution in the WAYF page
                        if not select_institution_if_present("initial WAYF"):
                            log.info("   [CARSI-Camofox] No usable institution search box found")

                        # Step 4: Wait for CAS login
                        _ak = _AUTH_KEYWORDS
                        _at = _AUTH_TITLES

                        url = page.url
                        title = page.title()
                        if any(x in url.lower() for x in _ak) or any(x in title for x in _at):
                            log.info("   [CARSI-Camofox] CAS login required. Please log in...")
                            for i in range(100):
                                time.sleep(3)
                                try:
                                    title = page.title()
                                    url = page.url
                                except Exception:
                                    return None
                                is_auth = any(x in title for x in _at)
                                is_auth_url = any(x in url.lower() for x in _ak)
                                if not is_auth and not is_auth_url:
                                    # Login success - save cookies in all formats + bridge to camofox-browser
                                    try:
                                        cookies = context.cookies()
                                        _save_all_cookie_formats(cookies, publisher, self.config)
                                    except Exception:
                                        pass
                                    break
                            else:
                                log.info("   [CARSI-Camofox] Login timed out")
                                return None
                        else:
                            log.info("   [CARSI-Camofox] Already authenticated")

                    # Step 5: Navigate to article (with CARSI auth now)
                    time.sleep(2)
                    log.info(f"   [CARSI-Camofox] Navigating to article: {article_url[:60]}")
                    try:
                        page.goto(article_url, wait_until="domcontentloaded", timeout=30000)
                        time.sleep(5)
                    except Exception:
                        pass

                    # Check for PDF via network capture
                    if captured_pdf:
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        output_path.write_bytes(captured_pdf[-1])
                        if is_pdf_file(output_path):
                            return _success(doi, output_path, "CARSI-Camofox")

                    # Step 6: Try direct PDF URL
                    pii_value = _extract_sciencedirect_pii(page.url, article_url, page.content())
                    pdf_pattern = cfg.pdf_pattern.replace("{doi}", doi).replace("{pii}", pii_value)
                    if pdf_pattern and not pdf_pattern.startswith("http"):
                        host = "www.sciencedirect.com" if publisher == "sciencedirect" else cfg.domains[0]
                        pdf_url = f"https://{host}{pdf_pattern}"
                    else:
                        pdf_url = pdf_pattern

                    if pdf_url and "{pii}" not in pdf_url and "/pii//" not in pdf_url:
                        log.info(f"   [CARSI-Camofox] Trying PDF: {pdf_url[:80]}")
                        captured_pdf.clear()
                        saved = fetch_pdf_via_page(pdf_url, "PDF fetch from article page")
                        if saved:
                            return saved
                        try:
                            pdf_response = page.goto(pdf_url, wait_until="commit", timeout=30000)
                            if pdf_response and pdf_response.status < 400:
                                saved = save_pdf_bytes(pdf_response.body(), "PDF navigation")
                                if saved:
                                    return saved
                            time.sleep(5)
                            if select_institution_if_present("PDF authorization"):
                                wait_for_login_if_needed("PDF authorization")
                                pdf_response = page.goto(pdf_url, wait_until="commit", timeout=30000)
                                if pdf_response and pdf_response.status < 400:
                                    saved = save_pdf_bytes(pdf_response.body(), "PDF navigation after institution")
                                    if saved:
                                        return saved
                                time.sleep(5)
                            for _pdf_wait in range(10):
                                current_title = page.title()
                                current_url = page.url
                                if (
                                    "请稍候" not in current_title
                                    and "just a moment" not in current_title.lower()
                                    and "pdf.sciencedirectassets.com" in current_url.lower()
                                ):
                                    break
                                if "pdf.sciencedirectassets.com" in current_url.lower():
                                    break
                                time.sleep(3)
                        except Exception:
                            pass
                        if captured_pdf:
                            saved = save_pdf_bytes(captured_pdf[-1], "network capture")
                            if saved:
                                return saved
                        saved = fetch_current_pdf_asset("ScienceDirect asset URL")
                        if saved:
                            return saved

                    # Step 7: Find PDF link in HTML
                    from ..pdf_utils import extract_pdf_url_from_html
                    try:
                        html = page.content()
                    except Exception as e:
                        log.info(f"   [CARSI-Camofox] Page content unavailable after PDF navigation: {e}")
                        time.sleep(3)
                        saved = fetch_current_pdf_asset("ScienceDirect asset after navigation")
                        if saved:
                            return saved
                        html = ""
                    found_pdf = _find_accessible_pdf_link(html, page.url, publisher)
                    if not found_pdf:
                        found_pdf = extract_pdf_url_from_html(html, page.url)
                    if found_pdf:
                        log.info(f"   [CARSI-Camofox] Found PDF link: {found_pdf[:80]}")
                        captured_pdf.clear()
                        try:
                            pdf_response = page.goto(found_pdf, wait_until="commit", timeout=30000)
                            if pdf_response and pdf_response.status < 400:
                                saved = save_pdf_bytes(pdf_response.body(), "PDF link navigation")
                                if saved:
                                    return saved
                            time.sleep(5)
                        except Exception:
                            pass
                        if captured_pdf:
                            saved = save_pdf_bytes(captured_pdf[-1], "network capture")
                            if saved:
                                return saved

                    # Step 8: Click PDF button
                    click_result = page.evaluate("""
                        () => {
                            const links = document.querySelectorAll('a');
                            for (const a of links) {
                                const href = (a.getAttribute('href') || '').toLowerCase();
                                const text = (a.innerText || '').toLowerCase();
                                if ((href.includes('pdf') || href.includes('download')) && !href.includes('supplement')) {
                                    if (text.includes('pdf') || text.includes('download')) {
                                        a.click();
                                        return a.href;
                                    }
                                }
                            }
                            return null;
                        }
                    """)
                    if click_result:
                        log.info(f"   [CARSI-Camofox] Clicked: {str(click_result)[:80]}")
                        time.sleep(8)
                        if captured_pdf:
                            output_path.parent.mkdir(parents=True, exist_ok=True)
                            output_path.write_bytes(captured_pdf[-1])
                            if is_pdf_file(output_path):
                                return _success(doi, output_path, "CARSI-Camofox")

                    saved = fetch_current_pdf_asset("final ScienceDirect asset URL")
                    if saved:
                        return saved

                    log.info(f"   [CARSI-Camofox] No PDF found. Title: {page.title()[:40]} URL: {page.url[:60]}")
                    return None

            except Exception as e:
                log.info(f"   [CARSI-Camofox] Error: {e}")
                return None

    def download_via_browser(self, doi: str, article_url: str, output_path: Path) -> dict[str, Any] | None:
        """Download PDF via browser in a single session (login + download).

        This avoids Cloudflare TLS fingerprinting issues by keeping everything
        in one browser session.
        """
        publisher = detect_publisher(article_url)
        if not publisher:
            return None

        cfg = self._publisher_configs.get(publisher)
        if not cfg:
            return None

        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
        except ImportError:
            log.info("   [CARSI-Browser] selenium not installed")
            return None

        download_dir = str(output_path.parent)
        options = Options()
        options.add_argument("--no-first-run")
        options.add_argument("--disable-gpu")
        options.add_argument("--remote-allow-origins=*")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "plugins.always_open_pdf_externally": True,
        }
        options.add_experimental_option("prefs", prefs)

        try:
            driver = webdriver.Chrome(options=options)
        except Exception as e:
            log.info(f"   [CARSI-Browser] Chrome launch failed: {e}")
            return None

        try:
            # Step 1: Navigate to institutional login
            driver.get(cfg.login_url)
            time.sleep(5)

            # Step 2: Search for institution
            idp_name = self.config.get("carsi_idp_name", "")
            if idp_name:
                search = driver.find_element(By.ID, "bdd-email")
                search.send_keys(idp_name[:10])  # Use first few chars
                time.sleep(3)
                # Click on institution
                driver.execute_script('''
                    var buttons = document.querySelectorAll("button");
                    for (var i = 0; i < buttons.length; i++) {
                        if (buttons[i].textContent.includes("''' + idp_name[:4] + '''")) {
                            buttons[i].click();
                            return true;
                        }
                    }
                    return false;
                ''')
                time.sleep(5)

            # Step 3: Wait for CAS login (user interaction)
            _login_keywords = ("cas", "login", "idp", "saml", "wayf", "auth", "sso", "passport", "accounts")
            url = driver.current_url
            if any(x in url.lower() for x in _login_keywords):
                log.info(f"   [CARSI-Browser] Please log in via CAS in the browser...")
                max_wait = 180
                elapsed = 0
                while elapsed < max_wait:
                    time.sleep(3)
                    elapsed += 3
                    try:
                        current = driver.current_url
                    except Exception:
                        return None
                    if not any(x in current.lower() for x in _login_keywords):
                        break
                else:
                    log.info("   [CARSI-Browser] Login timed out.")
                    return None

            # Step 4: Navigate to article
            time.sleep(2)
            driver.get(article_url)
            time.sleep(8)

            # Step 5: Check for PDF access
            body = driver.execute_script("return document.body.innerText")
            if "robot" in body.lower() or "captcha" in body.lower():
                log.info("   [CARSI-Browser] Bot detection triggered.")
                return None

            # Look for PDF download link
            links = driver.find_elements(By.CSS_SELECTOR, "a")
            for link in links:
                href = link.get_attribute("href") or ""
                text = link.text.strip().lower()
                if "pdf" in text and "purchase" not in text:
                    log.info(f"   [CARSI-Browser] Found PDF link: {href[:80]}")
                    driver.get(href)
                    time.sleep(5)
                    # Check if downloaded
                    from ..pdf_utils import is_pdf_file
                    downloaded = self._find_downloaded_pdf(download_dir, doi)
                    if downloaded:
                        return {"success": True, "path": str(downloaded), "source": "CARSI-Browser"}
                    break

            # Try pdfft pattern
            if publisher == "sciencedirect":
                import re
                pii_match = re.search(r"pii/([A-Z0-9]+)", article_url)
                if pii_match:
                    pdfft_url = f"https://www.sciencedirect.com/science/article/pii/{pii_match.group(1)}/pdfft"
                    driver.get(pdfft_url)
                    time.sleep(5)
                    from ..pdf_utils import is_pdf_file
                    downloaded = self._find_downloaded_pdf(download_dir, doi)
                    if downloaded:
                        return {"success": True, "path": str(downloaded), "source": "CARSI-Browser"}

        except Exception as e:
            log.info(f"   [CARSI-Browser] Error: {e}")
        finally:
            try:
                driver.quit()
            except Exception:
                pass
        return None

    def _find_downloaded_pdf(self, download_dir: str, doi: str) -> Path | None:
        """Check download directory for recently downloaded PDF files."""
        dir_path = Path(download_dir)
        if not dir_path.exists():
            return None
        now = time.time()
        for f in dir_path.iterdir():
            if f.suffix.lower() == ".pdf" and (now - f.stat().st_mtime) < 30:
                try:
                    if f.stat().st_size > 1000:
                        return f
                except OSError:
                    pass
        return None

    def _try_load_cookies(self, publisher: str) -> bool:
        cookie_file = self._cookie_path(publisher)
        if not cookie_file.exists():
            return False
        try:
            cookies = json.loads(cookie_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return False

        sess = self._get_session(publisher)
        for cookie in cookies:
            sess.cookies.set(
                cookie["name"],
                cookie["value"],
                domain=cookie.get("domain", ""),
                path=cookie.get("path", "/"),
            )
        return self._validate_session(publisher)

    def _validate_session(self, publisher: str) -> bool:
        cfg = self._publisher_configs.get(publisher)
        if not cfg:
            return False
        sess = self._get_session(publisher)

        # Check cookie file freshness — accept if < 24h old
        cookie_file = self._cookie_path(publisher)
        try:
            import os
            age_hours = (time.time() - os.path.getmtime(cookie_file)) / 3600
            if age_hours > 24:
                log.info(f"   [CARSI] Cookies for {publisher} expired ({age_hours:.1f}h old)")
                return False
        except OSError:
            return False

        # Validate by hitting a publisher page that requires auth
        # Use the main domain, not login_url (which always contains "login")
        try:
            test_url = f"https://{cfg.domains[0]}/"
            resp = sess.get(test_url, timeout=15, allow_redirects=True)
            # If we get redirected to a SSO/CAS/WAYF page, session is invalid
            url_lower = resp.url.lower()
            sso_keywords = ("wayf", "shibboleth", "saml", "idp.bayern", "passport")
            if any(k in url_lower for k in sso_keywords):
                return False
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def _browser_login(self, publisher: str) -> bool:
        """Login via CARSI by opening the publisher's institutional login page. Tries stealth browser first, falls back to Selenium."""
        cfg = self._publisher_configs.get(publisher)
        if not cfg:
            log.error(f"   [CARSI] Unknown publisher: {publisher}")
            return False

        # Try stealth browser (stealth browser) first
        try:
            from ..camofox_login import carsi_login
            if carsi_login(publisher, self.config, login_url=cfg.login_url, domains=cfg.domains):
                return True
        except Exception as exc:
            log.info(f"   [CARSI] stealth browser login failed: {exc}")

        # Fallback to Selenium
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
        except ImportError:
            log.error("   [CARSI] selenium not installed")
            return False

        idp_name = self.config.get("carsi_idp_name", "")
        log.info(f"   [CARSI] Opening {cfg.name} institutional login...")

        options = Options()
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--disable-gpu")
        options.add_argument("--remote-allow-origins=*")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])

        try:
            driver = webdriver.Chrome(options=options)
        except Exception as e:
            log.error(f"   [CARSI] Chrome launch failed: {e}")
            return False

        try:
            driver.get(cfg.login_url)
            log.info(f"   [CARSI] Please log in via {cfg.name} institutional access in the browser...")

            # Wait for user to complete login (up to 180 seconds)
            max_wait = 180
            elapsed = 0
            while elapsed < max_wait:
                time.sleep(3)
                elapsed += 3
                try:
                    url = driver.current_url
                except Exception:
                    log.info("   [CARSI] Browser closed by user.")
                    return False

                # Check if we're back on the publisher page (login successful)
                on_publisher = any(d in url for d in cfg.domains)
                on_login_page = any(x in url.lower() for x in ("login", "institutional", "wayf", "saml", "cas", "idp"))

                if on_publisher and not on_login_page:
                    # Save cookies
                    cookies = driver.get_cookies()
                    cookie_file = self._cookie_path(publisher)
                    cookie_data = [
                        {"name": c["name"], "value": c["value"], "domain": c.get("domain", ""), "path": c.get("path", "/")}
                        for c in cookies
                    ]
                    cookie_file.write_text(
                        json.dumps(cookie_data, indent=2, ensure_ascii=False),
                        encoding="utf-8",
                    )
                    log.info(f"   [CARSI] Login successful! Saved {len(cookie_data)} cookies.")
                    return True

            log.info("   [CARSI] Login timed out.")
            return False

        except Exception as e:
            log.error(f"   [CARSI] Login error: {e}")
            return False
        finally:
            try:
                driver.quit()
            except Exception:
                pass

    def _extract_chrome_cookies(self, publisher: str) -> None:
        """Try to extract cookies from Chrome's cookie database."""
        cfg = self._publisher_configs.get(publisher)
        if not cfg:
            return

        cookie_paths = [
            Path.home() / "AppData/Local/Google/Chrome/User Data/Default/Cookies",
            Path.home() / "AppData/Local/Google/Chrome/User Data/Default/Network/Cookies",
        ]

        for cookie_path in cookie_paths:
            if not cookie_path.exists():
                continue
            try:
                import shutil
                import sqlite3
                tmp_cookie = self._cookie_dir / "chrome_cookies_tmp.db"
                shutil.copy2(cookie_path, tmp_cookie)

                conn = sqlite3.connect(str(tmp_cookie))
                cursor = conn.cursor()

                cookies = []
                for domain in cfg.domains:
                    cursor.execute(
                        "SELECT name, value, host_key, path FROM cookies WHERE host_key LIKE ?",
                        (f"%{domain}%",),
                    )
                    cookies.extend(cursor.fetchall())
                conn.close()
                tmp_cookie.unlink(missing_ok=True)

                if cookies:
                    cookie_file = self._cookie_path(publisher)
                    cookie_data = [
                        {"name": n, "value": v, "domain": h, "path": p}
                        for n, v, h, p in cookies
                    ]
                    cookie_file.write_text(
                        json.dumps(cookie_data, indent=2, ensure_ascii=False),
                        encoding="utf-8",
                    )
                    log.info(f"   [CARSI] Extracted {len(cookie_data)} cookies from Chrome")
                    return
            except Exception as e:
                log.warning(f"   [CARSI] Chrome cookie extraction failed: {e}")

    def close(self):
        for sess in self._sessions.values():
            sess.close()
        self._sessions.clear()
