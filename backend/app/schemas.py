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
    houseSystem: str = "WHOLE_SIGN"
    ayanamsha: str = "LAHIRI"
    nodeType: str = "MEAN"
    include: IncludeFlags = IncludeFlags()

    @field_validator("houseSystem")
    @classmethod
    def _hs(cls, v):
        allowed = {"WHOLE_SIGN", "EQUAL", "PLACIDUS"}
        if v not in allowed: 
            raise ValueError(f"houseSystem must be one of {allowed}")
        return v

    @field_validator("ayanamsha")
    @classmethod
    def _ay(cls, v):
        allowed = {"LAHIRI", "RAMAN", "KRISHNAMURTI"}
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
    ayanamsha: str = "LAHIRI"
    depth: int = 3  # 1..3; default 3
    fromDate: Optional[str] = None  # ISO-8601 UTC (e.g., 1991-03-25T04:16:00Z)
    toDate: Optional[str] = None
    atDate: Optional[str] = None

    @field_validator("ayanamsha")
    @classmethod
    def _ay(cls, v):
        allowed = {"LAHIRI", "RAMAN", "KRISHNAMURTI"}
        if v not in allowed:
            raise ValueError(f"ayanamsha must be one of {allowed}")
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

    @field_validator("depth")
    @classmethod
    def _depth(cls, v):
        if v < 1 or v > 3:
            raise ValueError("depth must be between 1 and 3")
        return v
