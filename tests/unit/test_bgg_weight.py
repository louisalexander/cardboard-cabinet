import pytest
from app.bgg import _parse_avgweight

pytestmark = pytest.mark.unit


def test_parse_avgweight_reads_value():
    payload = {"item": {"stats": {"avgweight": "1.7717"}}}
    assert _parse_avgweight(payload) == pytest.approx(1.7717)


def test_parse_avgweight_zero_is_none():
    # BGG returns "0" for games with no weight votes — treat as unknown.
    assert _parse_avgweight({"item": {"stats": {"avgweight": "0"}}}) is None


def test_parse_avgweight_missing_stats_is_none():
    assert _parse_avgweight({"item": {"stats": {}}}) is None
    assert _parse_avgweight({"item": {}}) is None
    assert _parse_avgweight({}) is None


def test_parse_avgweight_malformed_is_none():
    assert _parse_avgweight({"item": {"stats": {"avgweight": "N/A"}}}) is None
    assert _parse_avgweight({"item": {"stats": {"avgweight": None}}}) is None
