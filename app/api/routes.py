from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from app.cache import TTLCache
from app.config import Settings, get_settings
from app.models.profile import ProfileRequest
from app.services.profile_service import ProfileService, ProfileServiceError

router = APIRouter()

_cache: TTLCache | None = None
_rate_buckets: dict[str, deque] = defaultdict(deque)


def get_cache(settings: Settings = Depends(get_settings)) -> TTLCache:
    global _cache
    if _cache is None:
        _cache = TTLCache(ttl_seconds=settings.CACHE_TTL_SECONDS)
    return _cache


def get_profile_service(
    settings: Settings = Depends(get_settings), cache: TTLCache = Depends(get_cache)
) -> ProfileService:
    return ProfileService(settings, cache)


def require_api_key(x_api_key: str = Header(default="")) -> None:
    settings = get_settings()
    if not settings.API_KEY:
        return  # no key configured -> API runs open (fine for local/demo use)
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED_OR_FORBIDDEN", "message": "Missing or invalid X-API-Key header."})


def enforce_rate_limit(x_api_key: str = Header(default="")) -> None:
    settings = get_settings()
    bucket_key = x_api_key or "anonymous"
    now = time.time()
    bucket = _rate_buckets[bucket_key]
    while bucket and now - bucket[0] > 60:
        bucket.popleft()
    if len(bucket) >= settings.RATE_LIMIT_PER_MINUTE:
        raise HTTPException(status_code=429, detail={"code": "UPSTREAM_RATE_LIMITED", "message": "Rate limit exceeded. Try again in a minute."})
    bucket.append(now)


@router.get("/health")
def health():
    settings = get_settings()
    return {"status": "ok", "linkedin_session_configured": settings.is_configured}


@router.get("/api")
def api_info():
    return {
        "name": "LinkedIn Profile API",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {"POST /v1/profile": "Accepts {\"url\": \"<linkedin profile url>\"}"},
    }


@router.post("/v1/profile", dependencies=[Depends(require_api_key), Depends(enforce_rate_limit)])
def post_profile(
    body: ProfileRequest,
    include_contact_info: bool = Query(False, description="Also attempt to fetch email/phone/websites (often privacy-restricted)"),
    service: ProfileService = Depends(get_profile_service),
):
    try:
        return service.get_profile(body.url, include_contact_info)
    except ProfileServiceError as exc:
        raise HTTPException(status_code=exc.http_status, detail={"code": exc.code, "message": exc.message})


@router.get("/v1/profile", dependencies=[Depends(require_api_key), Depends(enforce_rate_limit)])
def get_profile(
    url: str = Query(..., description="LinkedIn profile URL"),
    include_contact_info: bool = Query(False),
    service: ProfileService = Depends(get_profile_service),
):
    try:
        return service.get_profile(url, include_contact_info)
    except ProfileServiceError as exc:
        raise HTTPException(status_code=exc.http_status, detail={"code": exc.code, "message": exc.message})
