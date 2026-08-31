import json
from pathlib import Path

import pytest

from app.linkedin.parsers import certifications, education, experience, images, languages, profile, skills
from app.linkedin.resolver import EntityResolver

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def complete_resolver() -> EntityResolver:
    return EntityResolver(load("profile_view_complete.json"))


@pytest.fixture
def partial_resolver() -> EntityResolver:
    return EntityResolver(load("profile_view_partial.json"))


def test_profile_parser_complete(complete_resolver):
    result = profile.parse(complete_resolver, "https://www.linkedin.com/in/jane-doe-example/")
    assert result["name"] == "Jane Doe"
    assert result["headline"] == "Senior Software Engineer at Example Corp"
    assert result["location"] == "Bengaluru, Karnataka, India"
    assert result["public_id"] == "jane-doe-example"


def test_experience_parser_sorts_most_recent_first(complete_resolver):
    result = experience.parse(complete_resolver)
    assert len(result) == 2
    assert result[0]["company"] == "Example Corp"  # 2023 start, most recent
    assert result[1]["company"] == "Prior Co"
    assert result[0]["start_date"] == "2023-06"
    assert result[1]["end_date"] == "2023-05"


def test_education_parser(complete_resolver):
    result = education.parse(complete_resolver)
    assert result[0]["institution"] == "Example Institute of Technology"
    assert result[0]["field_of_study"] == "Computer Engineering"


def test_skills_parser(complete_resolver):
    assert skills.parse(complete_resolver) == ["Python", "Distributed Systems"]


def test_certifications_parser(complete_resolver):
    result = certifications.parse(complete_resolver)
    assert result[0]["name"] == "Certified Kubernetes Administrator"
    assert result[0]["issuer"] == "The Linux Foundation"


def test_languages_parser(complete_resolver):
    result = languages.parse(complete_resolver)
    assert result[0]["name"] == "English"


def test_images_parser_picks_highest_resolution(complete_resolver):
    result = images.parse(complete_resolver)
    assert result["profile"].endswith("400x400.jpg")


def test_partial_profile_has_no_optional_sections(partial_resolver):
    assert experience.parse(partial_resolver) == []
    assert education.parse(partial_resolver) == []
    assert skills.parse(partial_resolver) == []
    assert certifications.parse(partial_resolver) == []
    assert languages.parse(partial_resolver) == []
    # Core profile fields should still parse fine.
    core = profile.parse(partial_resolver, "https://www.linkedin.com/in/john-minimal/")
    assert core["name"] == "John Minimal"
