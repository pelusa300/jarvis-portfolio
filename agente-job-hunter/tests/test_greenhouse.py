# tests/test_greenhouse.py
from unittest.mock import patch, MagicMock

from scrapers.greenhouse import fetch_jobs, _is_relevant, _strip_html, _parse_date


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_job(title="AML Compliance Analyst",
              url="https://boards.greenhouse.io/coinbase/jobs/123",
              location="Remote",
              content="<p>Experience with <strong>Chainalysis</strong> required.</p>",
              updated_at="2026-04-27T10:00:00Z") -> dict:
    return {
        "title": title,
        "absolute_url": url,
        "location": {"name": location},
        "content": content,
        "updated_at": updated_at,
    }


def _mock_response(jobs: list) -> MagicMock:
    mock = MagicMock()
    mock.json.return_value = {"jobs": jobs}
    mock.raise_for_status.return_value = None
    return mock


# ---------------------------------------------------------------------------
# Unit tests for helper functions
# ---------------------------------------------------------------------------

class TestIsRelevant:
    def test_compliance_in_title(self):
        assert _is_relevant("Compliance Analyst") is True

    def test_aml_in_title(self):
        assert _is_relevant("Senior AML Investigator") is True

    def test_kyc_in_title(self):
        assert _is_relevant("KYC Manager") is True

    def test_sanctions_in_title(self):
        assert _is_relevant("Sanctions Screening Officer") is True

    def test_bsa_in_title(self):
        assert _is_relevant("BSA Officer") is True

    def test_regulatory_in_title(self):
        assert _is_relevant("Regulatory Affairs Lead") is True

    def test_risk_in_title(self):
        assert _is_relevant("Financial Risk Analyst") is True

    def test_fraud_in_title(self):
        assert _is_relevant("Fraud Investigator") is True

    def test_financial_crime_in_title(self):
        assert _is_relevant("Financial Crime Analyst") is True

    def test_case_insensitive(self):
        assert _is_relevant("COMPLIANCE OFFICER") is True
        assert _is_relevant("aml specialist") is True

    def test_irrelevant_title(self):
        assert _is_relevant("Software Engineer") is False

    def test_irrelevant_title_similar_words(self):
        assert _is_relevant("Senior Product Manager") is False


class TestStripHtml:
    def test_removes_tags(self):
        result = _strip_html("<p>Hello <strong>world</strong></p>")
        assert "<p>" not in result
        assert "world" in result

    def test_decodes_amp(self):
        result = _strip_html("AML &amp; KYC")
        assert "&amp;" not in result
        assert "AML & KYC" in result

    def test_empty_string(self):
        assert _strip_html("") == ""


class TestParseDate:
    def test_iso_datetime(self):
        assert _parse_date("2026-04-27T10:00:00Z") == "2026-04-27"

    def test_empty_string(self):
        assert _parse_date("") == ""

    def test_short_string(self):
        assert _parse_date("2026") == "2026"


# ---------------------------------------------------------------------------
# Integration-style tests (requests mocked)
# ---------------------------------------------------------------------------

class TestFetchJobs:
    def test_returns_list_with_relevant_jobs(self):
        mock_resp = _mock_response([_make_job()])

        with patch("scrapers.greenhouse.requests.get", return_value=mock_resp):
            jobs = fetch_jobs()

        assert isinstance(jobs, list)
        assert len(jobs) > 0

    def test_job_has_required_fields(self):
        mock_resp = _mock_response([_make_job()])

        with patch("scrapers.greenhouse.requests.get", return_value=mock_resp):
            jobs = fetch_jobs()

        required = {"title", "company", "location", "url", "description",
                    "source", "date_posted", "salary_min", "salary_max"}
        for job in jobs:
            assert required.issubset(job.keys()), f"Missing fields: {required - job.keys()}"

    def test_source_is_greenhouse(self):
        mock_resp = _mock_response([_make_job()])

        with patch("scrapers.greenhouse.requests.get", return_value=mock_resp):
            jobs = fetch_jobs()

        assert all(j["source"] == "greenhouse" for j in jobs)

    def test_salary_fields_are_none(self):
        mock_resp = _mock_response([_make_job()])

        with patch("scrapers.greenhouse.requests.get", return_value=mock_resp):
            jobs = fetch_jobs()

        for job in jobs:
            assert job["salary_min"] is None
            assert job["salary_max"] is None

    def test_irrelevant_jobs_filtered_out(self):
        irrelevant = _make_job(title="Software Engineer")
        mock_resp = _mock_response([irrelevant])

        with patch("scrapers.greenhouse.requests.get", return_value=mock_resp):
            jobs = fetch_jobs()

        assert jobs == []

    def test_only_relevant_jobs_kept(self):
        """Irrelevant jobs are filtered out; only compliance-related titles survive."""
        relevant = _make_job(title="AML Compliance Analyst")
        irrelevant = _make_job(title="DevOps Engineer",
                                url="https://boards.greenhouse.io/coinbase/jobs/999")
        # First company (coinbase) gets both jobs, remaining 6 get empty lists
        mock_mixed = _mock_response([relevant, irrelevant])
        mock_empty = _mock_response([])

        responses = [mock_mixed] + [mock_empty] * 6

        with patch("scrapers.greenhouse.requests.get", side_effect=responses):
            jobs = fetch_jobs()

        assert len(jobs) == 1
        assert "AML" in jobs[0]["title"]

    def test_html_stripped_from_description(self):
        job = _make_job(content="<p>Need <b>KYC</b> experience &amp; AML skills.</p>")
        mock_resp = _mock_response([job])

        with patch("scrapers.greenhouse.requests.get", return_value=mock_resp):
            jobs = fetch_jobs()

        desc = jobs[0]["description"]
        assert "<p>" not in desc
        assert "<b>" not in desc
        assert "KYC" in desc

    def test_date_parsed_correctly(self):
        job = _make_job(updated_at="2026-04-27T15:30:00Z")
        mock_resp = _mock_response([job])

        with patch("scrapers.greenhouse.requests.get", return_value=mock_resp):
            jobs = fetch_jobs()

        assert jobs[0]["date_posted"] == "2026-04-27"

    def test_silent_failure_on_network_error(self):
        with patch("scrapers.greenhouse.requests.get", side_effect=ConnectionError("timeout")):
            jobs = fetch_jobs()

        # All companies fail silently — result is empty list
        assert jobs == []

    def test_silent_failure_on_http_error(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("404 Not Found")

        with patch("scrapers.greenhouse.requests.get", return_value=mock_resp):
            jobs = fetch_jobs()

        assert jobs == []

    def test_empty_jobs_list_returns_empty(self):
        mock_resp = _mock_response([])

        with patch("scrapers.greenhouse.requests.get", return_value=mock_resp):
            jobs = fetch_jobs()

        assert jobs == []

    def test_multiple_companies_aggregated(self):
        """Jobs from different companies are all returned."""
        mock_resp = _mock_response([_make_job(title="KYC Analyst")])

        with patch("scrapers.greenhouse.requests.get", return_value=mock_resp):
            jobs = fetch_jobs()

        # 6 companies × 1 job each = 6 jobs
        assert len(jobs) == 6
