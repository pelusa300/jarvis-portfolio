# tests/test_indeed.py
from unittest.mock import patch, MagicMock

from scrapers.indeed import fetch_jobs, _split_title, _strip_html, _parse_pub_date


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rss_xml(items_xml: str) -> str:
    """Wraps item XML fragments in a minimal RSS envelope."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Indeed Jobs</title>
    {items_xml}
  </channel>
</rss>"""


def _make_item(title="AML Analyst - CryptoFirm - El Paso, TX",
               link="https://www.indeed.com/viewjob?jk=abc123",
               description="<p>Experience with <strong>Chainalysis</strong> required.</p>",
               pub_date="Mon, 27 Apr 2026 10:00:00 +0000") -> str:
    return f"""<item>
      <title>{title}</title>
      <link>{link}</link>
      <description>{description}</description>
      <pubDate>{pub_date}</pubDate>
    </item>"""


def _mock_response(xml_body: str) -> MagicMock:
    mock = MagicMock()
    mock.text = xml_body
    mock.raise_for_status.return_value = None
    return mock


# ---------------------------------------------------------------------------
# Unit tests for helper functions
# ---------------------------------------------------------------------------

class TestSplitTitle:
    def test_three_parts(self):
        t, c, l = _split_title("AML Analyst - CryptoFirm - El Paso, TX")
        assert t == "AML Analyst"
        assert c == "CryptoFirm"
        assert l == "El Paso, TX"

    def test_two_parts(self):
        t, c, l = _split_title("KYC Analyst - Coinbase")
        assert t == "KYC Analyst"
        assert c == "Coinbase"
        assert l == "Indeed"

    def test_one_part(self):
        t, c, l = _split_title("Compliance Officer")
        assert t == "Compliance Officer"
        assert c == "Indeed"
        assert l == "Indeed"


class TestStripHtml:
    def test_removes_tags(self):
        result = _strip_html("<p>Hello <strong>world</strong></p>")
        assert "<p>" not in result
        assert "<strong>" not in result
        assert "world" in result

    def test_decodes_entities(self):
        result = _strip_html("AML &amp; KYC &lt;required&gt;")
        assert "&amp;" not in result
        assert "&lt;" not in result
        assert "AML & KYC" in result

    def test_empty_string(self):
        assert _strip_html("") == ""


class TestParsePubDate:
    def test_valid_rfc2822(self):
        result = _parse_pub_date("Mon, 27 Apr 2026 10:00:00 +0000")
        assert result == "2026-04-27"

    def test_empty_string(self):
        assert _parse_pub_date("") == ""

    def test_invalid_date(self):
        assert _parse_pub_date("not-a-date") == ""


# ---------------------------------------------------------------------------
# Integration-style tests (requests mocked)
# ---------------------------------------------------------------------------

class TestFetchJobs:
    def test_returns_list_with_valid_rss(self):
        xml = _rss_xml(_make_item())
        mock_resp = _mock_response(xml)

        with patch("scrapers.indeed.requests.get", return_value=mock_resp):
            jobs = fetch_jobs()

        assert isinstance(jobs, list)
        assert len(jobs) > 0

    def test_job_has_required_fields(self):
        xml = _rss_xml(_make_item())
        mock_resp = _mock_response(xml)

        with patch("scrapers.indeed.requests.get", return_value=mock_resp):
            jobs = fetch_jobs()

        required = {"title", "company", "location", "url", "description",
                    "source", "date_posted", "salary_min", "salary_max"}
        for job in jobs:
            assert required.issubset(job.keys()), f"Missing fields: {required - job.keys()}"

    def test_source_is_indeed(self):
        xml = _rss_xml(_make_item())
        mock_resp = _mock_response(xml)

        with patch("scrapers.indeed.requests.get", return_value=mock_resp):
            jobs = fetch_jobs()

        assert all(j["source"] == "indeed" for j in jobs)

    def test_salary_fields_are_none(self):
        xml = _rss_xml(_make_item())
        mock_resp = _mock_response(xml)

        with patch("scrapers.indeed.requests.get", return_value=mock_resp):
            jobs = fetch_jobs()

        for job in jobs:
            assert job["salary_min"] is None
            assert job["salary_max"] is None

    def test_html_stripped_from_description(self):
        xml = _rss_xml(_make_item(description="<p>Need <b>AML</b> experience.</p>"))
        mock_resp = _mock_response(xml)

        with patch("scrapers.indeed.requests.get", return_value=mock_resp):
            jobs = fetch_jobs()

        desc = jobs[0]["description"]
        assert "<p>" not in desc
        assert "<b>" not in desc
        assert "AML" in desc

    def test_deduplication_across_feeds(self):
        """Same URL appearing in multiple feeds should be returned only once."""
        xml = _rss_xml(_make_item())
        mock_resp = _mock_response(xml)

        # All 5 feeds return the same single item → expect exactly 1 job
        with patch("scrapers.indeed.requests.get", return_value=mock_resp):
            jobs = fetch_jobs()

        urls = [j["url"] for j in jobs]
        assert len(urls) == len(set(urls)), "Duplicate URLs found"

    def test_silent_failure_on_network_error(self):
        with patch("scrapers.indeed.requests.get", side_effect=ConnectionError("timeout")):
            jobs = fetch_jobs()

        assert jobs == []

    def test_silent_failure_on_http_error(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("403 Forbidden")

        with patch("scrapers.indeed.requests.get", return_value=mock_resp):
            jobs = fetch_jobs()

        assert jobs == []

    def test_empty_rss_returns_empty_list(self):
        xml = _rss_xml("")
        mock_resp = _mock_response(xml)

        with patch("scrapers.indeed.requests.get", return_value=mock_resp):
            jobs = fetch_jobs()

        assert jobs == []

    def test_malformed_xml_returns_empty_list(self):
        mock_resp = _mock_response("this is not xml at all <<>>")

        with patch("scrapers.indeed.requests.get", return_value=mock_resp):
            jobs = fetch_jobs()

        assert jobs == []
