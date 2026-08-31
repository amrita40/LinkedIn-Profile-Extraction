from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse

from app.api.routes import router
from app.logging_config import configure_logging

configure_logging()

app = FastAPI(
    title="LinkedIn Profile API",
    description=(
        "Accepts a LinkedIn profile URL and returns structured JSON — name, "
        "headline, location, about, experience, education, skills, "
        "certifications, languages, and images — by making direct, "
        "authenticated HTTP requests to LinkedIn's internal API (no browser "
        "automation)."
    ),
    version="1.0.0",
)

app.include_router(router)

_STATIC_DIR = Path(__file__).parent / "static"


@app.get("/", include_in_schema=False)
def serve_demo_page():
    """The interactive demo page (app/static/index.html) at the root URL.
    JSON service info has moved to GET /api — see app/api/routes.py."""
    index_file = _STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse({"message": "Demo page not found — see /docs for the API."})


@app.exception_handler(HTTPException)
def http_exception_handler(request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        body = {"success": False, "error": detail}
    else:
        body = {"success": False, "error": {"code": "INTERNAL_ERROR", "message": str(detail)}}
    return JSONResponse(status_code=exc.status_code, content=body)


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"success": False, "error": {"code": "INVALID_LINKEDIN_URL", "message": str(exc)}},
    )


@app.exception_handler(Exception)
def unhandled_exception_handler(request, exc: Exception):
    # Never leak stack traces or upstream details to the client.
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred."}},
    )
