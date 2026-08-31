"""
Endpoint map
============

This is the output of the reverse-engineering phase: which internal
LinkedIn "Voyager" endpoints supply which required fields, established by
inspecting LinkedIn's own network requests while browsing a profile as a
logged-in user (browser used only for observation — the client below talks
to these endpoints directly via httpx, no browser at runtime).

Requirement                  -> Endpoint                                          -> Fields returned
----------------------------------------------------------------------------------------------------------
name, headline, location,       GET /voyager/api/identity/profiles/{id}/profileView   firstName, lastName,
about, profile image                                                                  headline, geoLocationName,
                                                                                        summary, profilePicture
experience                      (same call, bundled)                                  positions[] (title, company,
                                                                                        dates, location, description)
education                       (same call, bundled)                                  educations[] (school, degree,
                                                                                        field of study, dates)
skills                          (same call, bundled)                                  skills[] (name)
certifications                  (same call, bundled)                                  certifications[] (name,
                                                                                        authority, dates, url)
languages                       (same call, bundled)                                  languages[] (name, proficiency)
email / phone / websites        GET /voyager/api/identity/profiles/{id}/               emailAddress, phoneNumbers[],
(optional, privacy-gated)       profileContactInfo                                    websites[], twitterHandles[]

One request covers almost everything (Phase 2 requirement: minimize
requests) — `profileView` is a single normalized "card deck" response that
bundles the profile core plus every section listed above in its `included`
entity array (see resolver.py for how that's unpacked). Contact info is
deliberately a second, optional call: it's frequently hidden by the
profile owner's privacy settings, so we don't want a 403 there to fail the
whole request.

Both endpoints are undocumented, unversioned, and can change or be
throttled by LinkedIn without notice — see README "Known limitations".
"""
from __future__ import annotations

PROFILE_VIEW_PATH = "/voyager/api/identity/profiles/{public_id}/profileView"
CONTACT_INFO_PATH = "/voyager/api/identity/profiles/{public_id}/profileContactInfo"


def profile_view_url(public_id: str) -> str:
    return PROFILE_VIEW_PATH.format(public_id=public_id)


def contact_info_url(public_id: str) -> str:
    return CONTACT_INFO_PATH.format(public_id=public_id)
