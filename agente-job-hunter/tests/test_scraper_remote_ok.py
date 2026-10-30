# tests/test_scraper_remote_ok.py
from unittest.mock import patch, MagicMock

from scrapers.remote_ok import fetch_jobs


def _make_api_response(description_html: str, tags=None) -> list:
    """Returns a minimal Remote OK API response with one job."""
    return [
        {"legal": "disclaimer"},  # first element is metadata, ignored by scraper
        {
            "id": "123",
            "position": "AML Analyst",
            "company": "CryptoFirm",
            "url": "https://remoteok.com/jobs/123",
            "description": description_html,
            "tags": tags or [],
            "date": "2026-03-26T10:00:00Z",
            "salary_min": None,
            "salary_max": None,
        },
    ]


def test_html_tags_stripped_from_description():
    """HTML tags must not appear in the stored description."""
    html = "<p>Experience with <strong>Chainalysis</strong> required.</p>"
    api_response = _make_api_response(html)

    mock_resp = MagicMock()
    mock_resp.json.return_value = api_response
    mock_resp.raise_for_status.return_value = None

    with patch("scrapers.remote_ok.requests.get", return_value=mock_resp):
        jobs = fetch_jobs()

    assert len(jobs) == 1
    desc = jobs[0]["description"]
    assert "<p>" not in desc
    assert "</p>" not in desc
    assert "<strong>" not in desc


def test_skill_keywords_present_as_plain_text():
    """Skills embedded in HTML must be detectable as plain text after cleanup."""
    html = "<p>Must know <strong>Chainalysis</strong> and <em>SQL</em>.</p>"
    api_response = _make_api_response(html)

    mock_resp = MagicMock()
    mock_resp.json.return_value = api_response
    mock_resp.raise_for_status.return_value = None

    with patch("scrapers.remote_ok.requests.get", return_value=mock_resp):
        jobs = fetch_jobs()

    desc = jobs[0]["description"]
    assert "Chainalysis" in desc
    assert "SQL" in desc


def test_tags_still_appended_after_html_cleanup():
    """Tags from the API must still be appended to the description."""
    html = "<p>AML role</p>"
    api_response = _make_api_response(html, tags=["blockchain", "kyc"])

    mock_resp = MagicMock()
    mock_resp.json.return_value = api_response
    mock_resp.raise_for_status.return_value = None

    with patch("scrapers.remote_ok.requests.get", return_value=mock_resp):
        jobs = fetch_jobs()

    desc = jobs[0]["description"]
    assert "blockchain" in desc
    assert "kyc" in desc


def test_empty_description_handled_gracefully():
    """A job with no description must not raise an exception."""
    api_response = _make_api_response("")

    mock_resp = MagicMock()
    mock_resp.json.return_value = api_response
    mock_resp.raise_for_status.return_value = None

    with patch("scrapers.remote_ok.requests.get", return_value=mock_resp):
        jobs = fetch_jobs()

    assert len(jobs) == 1
    assert isinstance(jobs[0]["description"], str)
