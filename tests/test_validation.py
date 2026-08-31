import pytest

from app.services.validation import InvalidLinkedInUrlError, canonical_profile_url, extract_public_id


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://www.linkedin.com/in/satyanadella/", "satyanadella"),
        ("https://linkedin.com/in/satyanadella", "satyanadella"),
        ("linkedin.com/in/satyanadella?trk=public_profile", "satyanadella"),
        ("www.linkedin.com/in/jane-doe-12345/", "jane-doe-12345"),
    ],
)
def test_extract_public_id_accepts_valid_profile_urls(url, expected):
    assert extract_public_id(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/in/someone",  # wrong domain
        "https://www.linkedin.com/company/acme/",  # company page, not a profile
        "not a url at all",
        "",
        "https://www.linkedin.com/in/",  # no slug
    ],
)
def test_extract_public_id_rejects_invalid_urls(url):
    with pytest.raises(InvalidLinkedInUrlError):
        extract_public_id(url)


def test_canonical_profile_url():
    assert canonical_profile_url("jane-doe") == "https://www.linkedin.com/in/jane-doe/"
