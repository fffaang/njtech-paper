from scansci_pdf.publisher_strategies import (
    _COOKIE_CONSENT_DISMISS_JS,
    _IDP_MAP,
    _INSTITUTION_CLICK_JS,
    _extract_pdf_from_page,
    _institution_search_terms,
)
from scansci_pdf.sources.carsi import _extract_sciencedirect_pii, _find_accessible_pdf_link


def test_sciencedirect_view_pdf_link_with_pdfft_query_is_extracted():
    html = """
    <html>
      <body>
        <a class="link-button accessbar-utility-link"
           href="/science/article/pii/S1350630725010222/pdfft?md5=74027b512f0f96a29b477032473dd8f9&pid=1-s2.0-S1350630725010222-main.pdf">
          View PDF
        </a>
      </body>
    </html>
    """

    pdf_url = _extract_pdf_from_page(
        html,
        "https://www.sciencedirect.com/science/article/pii/S1350630725010222",
        "Elsevier",
    )

    assert pdf_url == (
        "https://www.sciencedirect.com/science/article/pii/S1350630725010222/"
        "pdfft?md5=74027b512f0f96a29b477032473dd8f9&pid=1-s2.0-S1350630725010222-main.pdf"
    )


def test_carsi_sciencedirect_uses_publisher_specific_pdf_link_detection():
    html = """
    <a href="/science/article/pii/S1350630725010222/pdfft?md5=abc&pid=1-s2.0-S1350630725010222-main.pdf">
      View PDF
    </a>
    """

    assert _find_accessible_pdf_link(
        html,
        "https://www.sciencedirect.com/science/article/pii/S1350630725010222",
        "sciencedirect",
    ).endswith("pdfft?md5=abc&pid=1-s2.0-S1350630725010222-main.pdf")


def test_sciencedirect_pii_extracted_from_linkinghub_retrieve_url():
    assert (
        _extract_sciencedirect_pii(
            "https://linkinghub.elsevier.com/retrieve/pii/S1350630725010222"
        )
        == "S1350630725010222"
    )


def test_sciencedirect_pii_extracted_from_pdf_filename_in_html():
    html = "pid=1-s2.0-S1350630725010222-main.pdf"

    assert _extract_sciencedirect_pii("https://www.sciencedirect.com", html) == "S1350630725010222"


def test_njtech_carsi_search_uses_nanjing_tech():
    assert _IDP_MAP["南京工业大学"] == "nanjing tech"


def test_njtech_carsi_search_terms_cover_elsevier_result_variants():
    terms = _institution_search_terms("南京工业大学")

    assert terms[:4] == [
        "nanjing tech",
        "nanjing tech university",
        "njtech",
        "南京工业大学",
    ]


def test_cookie_consent_dismiss_js_covers_elsevier_onetrust_banner():
    assert "#onetrust-accept-btn-handler" in _COOKIE_CONSENT_DISMISS_JS
    assert ".onetrust-close-btn-handler" in _COOKIE_CONSENT_DISMISS_JS
    assert "accept" in _COOKIE_CONSENT_DISMISS_JS.lower()
    assert "consent" in _COOKIE_CONSENT_DISMISS_JS.lower()


def test_institution_click_js_supports_elsevier_wayf_result_shapes():
    assert "terms" in _INSTITUTION_CLICK_JS
    assert "[role=\"option\"]" in _INSTITUTION_CLICK_JS
    assert "[data-testid]" in _INSTITUTION_CLICK_JS
    assert "offsetParent" in _INSTITUTION_CLICK_JS
    assert "dispatchEvent" in _INSTITUTION_CLICK_JS
