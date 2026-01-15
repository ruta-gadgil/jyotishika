from pydantic import BaseModel, Field, field_validator
from typing import Optional

class IncludeFlags(BaseModel):
    houseCusps: bool = False
    housesForEachPlanet: bool = True
    signsForEachPlanet: bool = True

class ChartRequest(BaseModel):
    datetime: str
    tz: Optional[str] = None
    utcOffsetMinutes: Optional[int] = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    houseSystem: Optional[str] = None
    ayanamsha: Optional[str] = None
    nodeType: str = "MEAN"
    include: IncludeFlags = IncludeFlags()
    profileName: Optional[str] = None  # Optional name for the profile (e.g., "My Chart", "John's Chart")

    @field_validator("houseSystem")
    @classmethod
    def _hs(cls, v):
        if v is None:
            return v
        allowed = {"WHOLE_SIGN", "EQUAL", "PLACIDUS"}
        if v not in allowed: 
            raise ValueError(f"houseSystem must be one of {allowed}")
        return v

    @field_validator("ayanamsha")
    @classmethod
    def _ay(cls, v):
        if v is None:
            return v
        allowed = {"LAHIRI", "RAMAN", "KRISHNAMURTI", "VEDANJANAM"}
        if v not in allowed:
            raise ValueError(f"ayanamsha must be one of {allowed}")
        return v

    @field_validator("nodeType")
    @classmethod
    def _nt(cls, v):
        allowed = {"MEAN", "TRUE"}
        if v not in allowed: 
            raise ValueError(f"nodeType must be one of {allowed}")
        return v

    @field_validator("datetime")
    @classmethod
    def _dt(cls, v):
        try:
            from datetime import datetime
            datetime.fromisoformat(v)
        except ValueError:
            raise ValueError("datetime must be in ISO-8601 format")
        return v

    @field_validator("tz")
    @classmethod
    def _tz(cls, v):
        if v is None:
            return v
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo(v)
        except Exception:
            raise ValueError(f"Invalid timezone: {v}")
        return v


# ---------------- Dasha API Schemas ----------------

class DashaRequest(BaseModel):
    datetime: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    depth: int = 3  # 1..3; default 3
    ayanamsha: Optional[str] = None
    fromDate: Optional[str] = None  # ISO-8601 UTC (e.g., 1991-03-25T04:16:00Z)
    toDate: Optional[str] = None
    atDate: Optional[str] = None

    @field_validator("datetime")
    @classmethod
    def _dt(cls, v):
        try:
            from datetime import datetime
            datetime.fromisoformat(v)
        except ValueError:
            raise ValueError("datetime must be in ISO-8601 format")
        return v

    @field_validator("ayanamsha")
    @classmethod
    def _ay(cls, v):
        if v is None:
            return v
        allowed = {"LAHIRI", "RAMAN", "KRISHNAMURTI", "VEDANJANAM"}
        if v not in allowed:
            raise ValueError(f"ayanamsha must be one of {allowed}")
        return v

    @field_validator("depth")
    @classmethod
    def _depth(cls, v):
        if v < 1 or v > 3:
            raise ValueError("depth must be between 1 and 3")
        return v


# ---------------- Profile Update API Schema ----------------

class ProfileUpdateRequest(BaseModel):
    """
    Schema for updating profile details.
    
    All fields are optional to support partial updates.
    Uses camelCase field names to match frontend conventions.
    """
    name: Optional[str] = None
    datetime: Optional[str] = None
    tz: Optional[str] = None
    utcOffsetMinutes: Optional[int] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    houseSystem: Optional[str] = None
    ayanamsha: Optional[str] = None
    nodeType: Optional[str] = None

    @field_validator("houseSystem")
    @classmethod
    def _hs(cls, v):
        if v is None:
            return v
        allowed = {"WHOLE_SIGN", "EQUAL", "PLACIDUS"}
        if v not in allowed: 
            raise ValueError(f"houseSystem must be one of {allowed}")
        return v

    @field_validator("ayanamsha")
    @classmethod
    def _ay(cls, v):
        if v is None:
            return v
        allowed = {"LAHIRI", "RAMAN", "KRISHNAMURTI", "VEDANJANAM"}
        if v not in allowed:
            raise ValueError(f"ayanamsha must be one of {allowed}")
        return v

    @field_validator("nodeType")
    @classmethod
    def _nt(cls, v):
        if v is None:
            return v
        allowed = {"MEAN", "TRUE"}
        if v not in allowed: 
            raise ValueError(f"nodeType must be one of {allowed}")
        return v

    @field_validator("datetime")
    @classmethod
    def _dt(cls, v):
        if v is None:
            return v
        try:
            from datetime import datetime
            datetime.fromisoformat(v)
        except ValueError:
            raise ValueError("datetime must be in ISO-8601 format")
        return v

    @field_validator("tz")
    @classmethod
    def _tz(cls, v):
        if v is None:
            return v
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo(v)
        except Exception:
            raise ValueError(f"Invalid timezone: {v}")
        return v


# ---------------- Analysis Notes API Schemas ----------------

class AnalysisNoteCreate(BaseModel):
    """
    Schema for creating a new analysis note.
    
    Validates title and note fields with length constraints.
    """
    title: str = Field(min_length=1, max_length=200)
    note: str = Field(min_length=0, max_length=5000)
    
    @field_validator("title")
    @classmethod
    def _title(cls, v):
        # Strip whitespace and validate
        v = v.strip()
        if not v:
            raise ValueError("title cannot be empty or only whitespace")
        return v


class AnalysisNoteUpdate(BaseModel):
    """
    Schema for updating an existing analysis note.
    
    All fields are optional to support partial updates.
    """
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    note: Optional[str] = Field(default=None, min_length=0, max_length=5000)
    
    @field_validator("title")
    @classmethod
    def _title(cls, v):
        if v is None:
            return v
        # Strip whitespace and validate
        v = v.strip()
        if not v:
            raise ValueError("title cannot be empty or only whitespace")
        return v
