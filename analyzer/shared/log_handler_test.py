import pytest
from log_handler import _redact_url_params


@pytest.mark.parametrize("input_text, expected", [
    # Single query param
    (
        "for url 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key=AIzaSyAfYK8A_sCzZ6uKKfzJ_etn_MeWT9oruAk'",
        "for url 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key=***'",
    ),
    # Multiple query params
    (
        "GET https://abc.de/script?aa=val1&bb=val2&cc=val3",
        "GET https://abc.de/script?aa=***&bb=***&cc=***",
    ),
    # No query params — unchanged
    (
        "GET https://abc.de/script",
        "GET https://abc.de/script",
    ),
    # Non-URL text with = signs — unchanged
    (
        'result: {"status": "ok", "count": 42, "key": "somevalue"}',
        'result: {"status": "ok", "count": 42, "key": "somevalue"}',
    ),
    # Multiple URLs on one line
    (
        "first https://a.com/x?token=secret then https://b.com/y?api_key=abc123",
        "first https://a.com/x?token=*** then https://b.com/y?api_key=***",
    ),
    # No URL at all — unchanged
    (
        "plain log line with no url",
        "plain log line with no url",
    ),
])
def test_redact_url_params(input_text, expected):
    assert _redact_url_params(input_text) == expected
