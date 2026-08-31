# LinkedIn Profile API

## Overview

A hosted API that accepts a LinkedIn profile URL and returns structured
JSON — name, headline, location, about, experience, education, skills,
certifications, languages, and images. It works by making **direct,
authenticated HTTP requests to LinkedIn's internal "Voyager" API** — the
same undocumented JSON API LinkedIn's own web app calls under the hood.
There is no browser automation anywhere in the deployed service (no
Playwright/Selenium/Puppeteer, no DOM scraping) — a browser is used only
once, manually, to observe the network requests and lift a session cookie.

## Features

- Direct HTTP requests to LinkedIn via `httpx` — no browser at runtime
- Structured, self-designed JSON schema (not a raw LinkedIn dump)
- Experience, education, skills, certifications, languages, images
- Optional contact-info lookup (email/phone/websites — often privacy-gated)
- URL validation (rejects anything that isn't `linkedin.com/in/<slug>`)
- Clear, typed error codes with no leaked internals
- Graceful partial-data handling — missing sections never 500
- In-memory TTL cache to avoid re-hitting LinkedIn for repeat lookups
- Simple API-key + rate-limit protection for the hosted endpoint itself
- Dockerized, environment-variable configuration, `.env.example`
- 29 automated tests, all running against fixtures (no live network calls)
- One retry with backoff on transient LinkedIn errors (timeouts, 5xx only —
  never on 401/403/404/429, which are meaningful signals, not glitches)
- Structured logging that never writes secrets, headers, or cookies to logs
- `/docs` interactive Swagger UI, `/health` liveness check
- An interactive demo page at `/` — paste a profile URL, see the live
  request/response, no separate client needed

## Architecture

```
Client
  |
  | POST /v1/profile  {"url": "..."}
  v
FastAPI  (app/api/routes.py)
  |  - API key check, rate limit
  |  - validates request shape
  v
ProfileService  (app/services/profile_service.py)
  |  - validates & normalizes the URL      -> app/services/validation.py
  |  - cache lookup                        -> app/cache.py
  |  - on miss, calls LinkedInClient
  v
LinkedInClient  (app/linkedin/client.py)
  |  - authenticated httpx.Client          -> app/linkedin/auth.py
  |  - GET profileView                     -> app/linkedin/endpoints.py
  |  - GET profileContactInfo (optional)
  v
Raw LinkedIn JSON (normalized entity graph: `data` + `included[]`)
  |
  v
EntityResolver  (app/linkedin/resolver.py)
  |  - indexes `included` by entityUrn
  |  - filters entities by $type
  v
Section parsers  (app/linkedin/parsers/*.py)
  |  profile.py  experience.py  education.py
  |  skills.py   certifications.py  languages.py  images.py
  v
ProfileService assembles the final envelope
  |
  v
Pydantic response models  (app/models/profile.py)
  |
  v
{"success": true, "data": {...}, "metadata": {...}}
```

Each layer has one job and doesn't reach into the next: routes never touch
`httpx`, the LinkedIn client never knows about the response schema, and
parsers never make network calls. This is what makes the LinkedIn-facing
code (the part most likely to break when LinkedIn changes something)
swappable without touching the API surface.

## Reverse-engineering approach

LinkedIn's profile pages are a single-page app that calls an internal API
at `https://www.linkedin.com/voyager/api/*` — there's no official public
"give me a profile as JSON" endpoint outside LinkedIn's paid partner
programs, so this is the only way to get structured data programmatically.
This is the same API that essentially every third-party LinkedIn tool
(including the PhantomBuster automation referenced in the brief) talks to.

**How the endpoints were identified:** log into linkedin.com in a browser,
open DevTools → Network → filter `voyager`, visit a profile, and read the
requests the page itself makes. The two relevant ones:

| Endpoint | What it returns |
|---|---|
| `GET /voyager/api/identity/profiles/{id}/profileView` | One normalized response bundling profile core (name, headline, location, about, images) **and** experience, education, skills, certifications, and languages, all in its `included[]` array |
| `GET /voyager/api/identity/profiles/{id}/profileContactInfo` | Email, phone, websites — separate call because it's frequently hidden by the profile owner's privacy settings |

Full detail (auth mechanics, headers required) lives in
`app/linkedin/auth.py` and `app/linkedin/endpoints.py` as code comments
next to the implementation, so the documentation can't drift from the code.

**Why one call covers almost everything:** Voyager doesn't return flat
JSON — it returns a `data` object plus an `included` array holding every
entity referenced anywhere in the response, each tagged with an
`entityUrn` and a `$type` (e.g. `...identity.profile.Position`). Rather
than issuing a separate request per section, `EntityResolver` indexes
`included` once and each parser asks it for "every entity whose `$type`
contains `Position`" and so on. This keeps LinkedIn requests to one or two
per profile lookup, which matters both for latency and for not drawing
unnecessary attention to the session.

**Auth, without touching a password:** LinkedIn's own login flow is
protected by device fingerprinting and CAPTCHA/MFA challenges designed to
stop scripted logins — and this project doesn't attempt to defeat any of
that. Instead it reuses the two cookies (`li_at`, `JSESSIONID`) LinkedIn
already issues to a normal, human, authorized login in a browser, exactly
the way the browser itself re-sends them on every page load. No password,
CAPTCHA, or MFA step is ever scripted or bypassed — see `app/linkedin/auth.py`.

**Normalization:** raw Voyager JSON is never returned to the client. It's
resolved and reshaped by the parsers in `app/linkedin/parsers/` into the
schema below, so the public API contract stays stable even if LinkedIn
renames or restructures internal fields — only the parsers would need to
change.

## API documentation

### `POST /v1/profile`

```bash
curl -X POST https://YOUR-DOMAIN/v1/profile \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_KEY" \
  -d '{"url": "https://www.linkedin.com/in/example/"}'
```

`GET /v1/profile?url=...` is also supported, for quick browser/curl testing.

Query param `include_contact_info=true` additionally attempts the
contact-info lookup (off by default, since it's an extra LinkedIn request
that's frequently privacy-restricted anyway).

**Success response — `200`:**

```json
{
  "success": true,
  "data": {
    "profile": {
      "url": "https://www.linkedin.com/in/example/",
      "public_id": "example",
      "name": "Jane Doe",
      "headline": "Senior Software Engineer at Example Corp",
      "location": "Bengaluru, Karnataka, India",
      "industry": "Software Development",
      "about": "Backend engineer focused on distributed systems..."
    },
    "images": {
      "profile": "https://media.licdn.com/dms/image/.../400x400.jpg",
      "background": null
    },
    "experience": [
      {
        "title": "Senior Software Engineer",
        "company": "Example Corp",
        "company_url": null,
        "location": "Bengaluru, India",
        "employment_type": "Full-time",
        "start_date": "2023-06",
        "end_date": null,
        "description": "Leading backend platform initiatives."
      }
    ],
    "education": [
      {
        "institution": "Example Institute of Technology",
        "degree": "B.Tech",
        "field_of_study": "Computer Engineering",
        "grade": null,
        "start_date": "2017",
        "end_date": "2021",
        "description": null
      }
    ],
    "skills": ["Python", "Distributed Systems"],
    "certifications": [
      {
        "name": "Certified Kubernetes Administrator",
        "issuer": "The Linux Foundation",
        "issue_date": "2022-09",
        "credential_url": "https://example.org/verify/123"
      }
    ],
    "languages": [
      {"name": "English", "proficiency": "Native or bilingual proficiency"}
    ],
    "contact_info": null
  },
  "metadata": {
    "source": "linkedin",
    "retrieved_at": "2026-08-29T10:15:00+00:00",
    "status": "complete",
    "missing_sections": [],
    "cached": false
  }
}
```

**Error responses** — always this shape, never a stack trace or upstream detail:

```json
{"success": false, "error": {"code": "INVALID_LINKEDIN_URL", "message": "..."}}
```

| HTTP | code | Meaning |
|---|---|---|
| 400 | `INVALID_LINKEDIN_URL` | Not a `linkedin.com/in/<slug>` URL |
| 401 | `UNAUTHORIZED_OR_FORBIDDEN` | Missing/bad `X-API-Key`, or LinkedIn rejected the session |
| 404 | `PROFILE_NOT_FOUND` | Profile doesn't exist or isn't visible to this account |
| 429 | `UPSTREAM_RATE_LIMITED` | Either this API's own rate limit, or LinkedIn throttled the session |
| 502 | `LINKEDIN_UPSTREAM_ERROR` | LinkedIn returned something unexpected |
| 503 | `SERVICE_NOT_CONFIGURED` | Server has no `LI_AT`/`JSESSIONID` set |
| 500 | `INTERNAL_ERROR` | Unhandled error — no internals are ever exposed |

### `GET /health`
`{"status": "ok", "linkedin_session_configured": true}`

### `GET /`
The interactive demo page (`app/static/index.html`) — a live terminal-style
panel to paste a profile URL and see the real request/response, plus the
schema reference and usage notice below. Configurable API base URL/key for
testing against a deployment other than the one serving the page.

### `GET /api`
Basic service info + links to `/docs` and `/health`.

### `GET /docs`
Interactive Swagger UI (FastAPI auto-generated).

## Local setup

```bash
git clone <this-repo-url>
cd linkedin-profile-api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in LI_AT / JSESSIONID, see below
uvicorn app.main:app --reload
```

### Getting `LI_AT` and `JSESSIONID`

1. Log into linkedin.com in a normal browser, using the account you're
   authorized to use for this.
2. Open DevTools → Application (Chrome) / Storage (Firefox) → Cookies →
   `https://www.linkedin.com`.
3. Copy the value of `li_at`.
4. Copy the value of `JSESSIONID` (it looks like `ajax:1234567890123456789`,
   quotes included or not — the app handles both).
5. Put both in `.env`.

These expire after roughly a year of inactivity, or immediately if you log
out of that browser session — see "Known limitations".

## Environment variables (`.env.example`)

| Variable | Required | Purpose |
|---|---|---|
| `LI_AT` | yes | LinkedIn session cookie |
| `JSESSIONID` | yes | LinkedIn session cookie / CSRF token source |
| `API_KEY` | no | If set, clients must send it as `X-API-Key`. Blank = API runs open |
| `CACHE_TTL_SECONDS` | no | Default `3600` |
| `RATE_LIMIT_PER_MINUTE` | no | Default `20`, per API key/IP |
| `REQUEST_TIMEOUT_SECONDS` | no | Default `15` |

`.env` is git-ignored; only `.env.example` (with blank values) is committed.

## Docker

```bash
docker build -t linkedin-profile-api .
docker run -p 8000:8000 --env-file .env linkedin-profile-api
```

or with Compose: `docker compose up --build`. The image installs only
`requirements.txt` — no browser binaries, since the deployed service never
launches one.

## Testing

```bash
pip install -r requirements.txt pytest
pytest -v
```

29 tests, all offline:

- `tests/test_validation.py` — URL validation/normalization directly, both
  accepted and rejected shapes
- `tests/test_parsers.py` — each section parser against sanitized,
  representative Voyager-shaped fixtures (`tests/fixtures/*.json`),
  covering both a complete profile and one with every optional section missing
- `tests/test_client.py` — `LinkedInClient` against an `httpx.MockTransport`,
  covering 200/404/401/429 responses without any real network call
- `tests/test_api.py` — full request/response cycle through FastAPI with a
  fake LinkedIn client injected, covering validation errors, the
  not-configured case, a successful lookup, and cache behavior

No test ever depends on a live LinkedIn session or network access.

## Deployment

Any container host works (Render, Railway, Fly.io, a plain VPS + `docker
run` behind Caddy/nginx for TLS). Steps are the same everywhere:

1. Push this repo to your host, or point it at the Dockerfile.
2. Set `LI_AT`, `JSESSIONID`, and (recommended for a public deployment)
   `API_KEY` as the platform's encrypted environment variables — never in
   the repo.
3. Point the platform's HTTPS termination at container port `8000`.
4. Verify: `curl https://YOUR-DOMAIN/health` and `https://YOUR-DOMAIN/docs`.

## Known limitations

- **Undocumented, unversioned upstream.** `/voyager/api/*` is LinkedIn's
  internal API, not a public contract. LinkedIn can change field names,
  response shapes, or remove endpoints without notice — this is the
  single biggest risk to this project's reliability, by design of using a
  reverse-engineered API at all. The parsers are defensive (missing
  fields degrade to `null`/`[]`, never a crash) but a large enough schema
  change would need a parser update to keep working.
- **Session cookies expire / can be invalidated.** `li_at` is long-lived
  (~1 year) but is invalidated by logging out that session, a password
  change, or LinkedIn flagging the session as suspicious. When that
  happens every request fails with `401 UNAUTHORIZED_OR_FORBIDDEN` until
  the cookies are refreshed manually.
- **Rate limiting / throttling risk.** Heavy use of one session's cookies
  for automated requests is exactly the kind of pattern LinkedIn's
  anti-abuse systems are built to catch, and can lead to challenges,
  throttling, or the account being restricted. The built-in cache and
  per-key rate limit reduce this but don't eliminate it — this is a
  structural risk of the whole approach, not a bug.
- **Profile visibility.** Only profiles the authenticated account is
  actually allowed to view (per LinkedIn's own visibility settings,
  connection degree, etc.) can be fetched; others come back as
  `404 PROFILE_NOT_FOUND` even if the URL is valid.
- **Partial data is normal, not an error.** Skills, certifications, and
  languages are frequently empty on real profiles; `metadata.status` will
  read `"partial"` and `missing_sections` will list what's absent — this
  is expected LinkedIn data sparsity, not a parsing failure.
- **Contact info is usually restricted.** Most users hide email/phone/
  websites from anyone outside their immediate network, so
  `contact_info` is commonly `null` even with `include_contact_info=true`.
- **Single-instance cache.** The TTL cache is in-process memory — fine for
  one instance, but won't be shared across multiple replicas. Swapping in
  Redis (the interface in `app/cache.py` is deliberately small) is the
  natural next step for horizontal scaling.
- **Terms of Service.** Programmatic access to LinkedIn outside its
  official partner APIs is against LinkedIn's User Agreement, and
  LinkedIn has pursued legal action against scrapers in the past (e.g.
  its dispute with hiQ Labs, and more recently against Meta over a similar
  scraping tool). This carries real account and legal risk for whoever's
  session is configured — worth being upfront about when this project is
  discussed or submitted.

## Security

- No password, CAPTCHA-bypass, or MFA-bypass logic exists anywhere in
  this codebase — the client only replays an already-authenticated
  session's cookies, exactly as a browser does.
- `LI_AT` / `JSESSIONID` / `API_KEY` are read only from environment
  variables (`app/config.py`); nothing is hardcoded, and `.env` is
  git-ignored — only `.env.example` (blank) is committed.
- Error responses are a fixed `{code, message}` shape and never include
  headers, cookies, stack traces, or raw upstream bodies (see the
  catch-all handler in `app/main.py`).
- Client-facing log lines never include headers or cookie values (see
  `app/linkedin/client.py`), only the request path and error class.
- The hosted endpoint itself can be protected with `API_KEY` +
  per-key rate limiting (`app/api/routes.py`) — separate from, and in
  addition to, LinkedIn's own session.
