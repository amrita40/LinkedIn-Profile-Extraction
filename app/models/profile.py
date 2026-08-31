from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class ProfileRequest(BaseModel):
    url: str


class ExperienceItem(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    company_url: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None


class EducationItem(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    grade: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None


class CertificationItem(BaseModel):
    name: Optional[str] = None
    issuer: Optional[str] = None
    issue_date: Optional[str] = None
    credential_url: Optional[str] = None


class LanguageItem(BaseModel):
    name: Optional[str] = None
    proficiency: Optional[str] = None


class ProfileCore(BaseModel):
    url: str
    public_id: Optional[str] = None
    name: Optional[str] = None
    headline: Optional[str] = None
    location: Optional[str] = None
    industry: Optional[str] = None
    about: Optional[str] = None


class ImageSet(BaseModel):
    profile: Optional[str] = None
    background: Optional[str] = None


class ContactInfo(BaseModel):
    email: Optional[str] = None
    phone_numbers: list[str] = []
    websites: list[str] = []


class ProfileData(BaseModel):
    profile: ProfileCore
    images: ImageSet
    experience: list[ExperienceItem] = []
    education: list[EducationItem] = []
    skills: list[str] = []
    certifications: list[CertificationItem] = []
    languages: list[LanguageItem] = []
    contact_info: Optional[ContactInfo] = None


class Metadata(BaseModel):
    source: str = "linkedin"
    retrieved_at: str
    status: str  # "complete" | "partial" | "cached"
    missing_sections: list[str] = []
    cached: bool = False


class ProfileSuccessResponse(BaseModel):
    success: bool = True
    data: ProfileData
    metadata: Metadata


class ApiError(BaseModel):
    code: str
    message: str


class ProfileErrorResponse(BaseModel):
    success: bool = False
    error: ApiError
