import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock
from tracker.freshness import check_link, is_stale, flag_stale


# ── is_stale ─────────────────────────────────────────────────────────────

def test_is_stale_true():
    old = (date.today() - timedelta(days=22)).isoformat()
    assert is_stale(old) is True


def test_is_stale_false():
    recent = (date.today() - timedelta(days=10)).isoformat()
    assert is_stale(recent) is False


def test_is_stale_today():
    assert is_stale(date.today().isoformat()) is False


def test_is_stale_empty():
    assert is_stale("") is False


def test_is_stale_bad_format():
    assert is_stale("not-a-date") is False


def test_flag_stale_adds_flag():
    old = (date.today() - timedelta(days=25)).isoformat()
    jobs = [
        {"date_found": old, "title": "T1"},
        {"date_found": date.today().isoformat(), "title": "T2"},
    ]
    result = flag_stale(jobs)
    assert result[0]["stale"] is True
    assert result[1]["stale"] is False


# ── check_link — HEAD normal ──────────────────────────────────────────────

def test_check_link_head_404_returns_cerrada():
    resp = MagicMock(status_code=404)
    with patch("tracker.freshness.requests.head", return_value=resp):
        assert check_link("https://example.com/job") == "cerrada"


def test_check_link_head_200_returns_ok():
    resp = MagicMock(status_code=200, text="Apply now!")
    with patch("tracker.freshness.requests.head", return_value=resp):
        assert check_link("https://example.com/job") == "ok"


def test_check_link_exception_returns_no_verificado():
    with patch("tracker.freshness.requests.head", side_effect=Exception("timeout")):
        assert check_link("https://example.com/job") == "no verificado"


def test_check_link_empty_url():
    assert check_link("") == "no verificado"
    assert check_link(None) == "no verificado"


# ── check_link — HEAD 405/403 → retry GET ────────────────────────────────

def test_check_link_head_405_retries_get_ok():
    head_resp = MagicMock(status_code=405)
    get_resp = MagicMock(status_code=200, text="Apply now for this role!")
    with patch("tracker.freshness.requests.head", return_value=head_resp), \
         patch("tracker.freshness.requests.get", return_value=get_resp):
        assert check_link("https://example.com/job") == "ok"


def test_check_link_head_403_retries_get_ok():
    head_resp = MagicMock(status_code=403)
    get_resp = MagicMock(status_code=200, text="Open position available")
    with patch("tracker.freshness.requests.head", return_value=head_resp), \
         patch("tracker.freshness.requests.get", return_value=get_resp):
        assert check_link("https://example.com/job") == "ok"


def test_check_link_head_403_get_404_returns_cerrada():
    head_resp = MagicMock(status_code=403)
    get_resp = MagicMock(status_code=404)
    with patch("tracker.freshness.requests.head", return_value=head_resp), \
         patch("tracker.freshness.requests.get", return_value=get_resp):
        assert check_link("https://example.com/job") == "cerrada"


def test_check_link_head_405_get_body_closed_phrase():
    head_resp = MagicMock(status_code=405)
    get_resp = MagicMock(status_code=200, text="This job is no longer available.")
    with patch("tracker.freshness.requests.head", return_value=head_resp), \
         patch("tracker.freshness.requests.get", return_value=get_resp):
        assert check_link("https://example.com/job") == "cerrada"


def test_check_link_head_403_get_body_position_filled():
    head_resp = MagicMock(status_code=403)
    get_resp = MagicMock(status_code=200, text="Position has been filled.")
    with patch("tracker.freshness.requests.head", return_value=head_resp), \
         patch("tracker.freshness.requests.get", return_value=get_resp):
        assert check_link("https://example.com/job") == "cerrada"


def test_check_link_head_405_get_exception_returns_no_verificado():
    head_resp = MagicMock(status_code=405)
    with patch("tracker.freshness.requests.head", return_value=head_resp), \
         patch("tracker.freshness.requests.get", side_effect=Exception("conn error")):
        assert check_link("https://example.com/job") == "no verificado"


def test_check_link_head_200_no_get_called():
    head_resp = MagicMock(status_code=200, text="Apply now!")
    with patch("tracker.freshness.requests.head", return_value=head_resp) as mock_head, \
         patch("tracker.freshness.requests.get") as mock_get:
        result = check_link("https://example.com/job")
    assert result == "ok"
    mock_get.assert_not_called()
