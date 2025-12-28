from testsuites.api_testing.framework.http_client import HttpClient


def test_redact_headers_masks_sensitive_values():
    client = object.__new__(HttpClient)  # bypass __init__
    masked = client._redact_headers(
        {
            "Authorization": "secret-token",
            "x-api-key": "apikey",
            "Cookie": "session=abc",
            "X-Other": "keep",
        }
    )
    assert masked["Authorization"] == "***MASKED***"
    assert masked["x-api-key"] == "***MASKED***"
    assert masked["Cookie"] == "***MASKED***"
    assert masked["X-Other"] == "keep"


def test_redact_body_masks_sensitive_fields():
    client = object.__new__(HttpClient)
    payload = {
        "password": "p1",
        "nested": {"token": "tok", "keep": "value"},
        "items": [{"api_key": "k1"}, {"regular": "ok"}],
    }
    redacted = client._redact_body(payload)

    assert redacted["password"] == "***MASKED***"
    assert redacted["nested"]["token"] == "***MASKED***"
    assert redacted["nested"]["keep"] == "value"
    assert redacted["items"][0]["api_key"] == "***MASKED***"
    assert redacted["items"][1]["regular"] == "ok"

