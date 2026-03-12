import swisseph as swe

PLANETS = [
    ("Sun", swe.SUN),
    ("Moon", swe.MOON),
    ("Mercury", swe.MERCURY),
    ("Venus", swe.VENUS),
    ("Mars", swe.MARS),
    ("Jupiter", swe.JUPITER),
    ("Saturn", swe.SATURN),
    ("Uranus", swe.URANUS),
    ("Neptune", swe.NEPTUNE),
    ("Pluto", swe.PLUTO),
    ("Rahu", "NODE"),   # special handling
    ("Ketu", "KETU"),   # derived
]

AYANAMSHA = {
    "LAHIRI": swe.SIDM_LAHIRI,
    "RAMAN": swe.SIDM_RAMAN,
    "KRISHNAMURTI": swe.SIDM_KRISHNAMURTI,
    "VEDANJANAM": swe.SIDM_LAHIRI,  # Custom: Lahiri + 6 arc minutes
}

HOUSE_CODES = {"WHOLE_SIGN": "W", "EQUAL": "E", "PLACIDUS": "P"}

# Swiss Ephemeris calculation flags
SEFLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_SIDEREAL

# Mean daily motions in degrees/day
PLANET_MEAN_SPEEDS = {
    "Sun": 0.9856,
    "Moon": 13.1763,
    "Mercury": 1.3833,
    "Venus": 1.2000,
    "Mars": 0.5241,
    "Jupiter": 0.0831,
    "Saturn": 0.0335,
    "Rahu": -0.0529,
    "Ketu": -0.0529,
    "Uranus": 0.0115,    # 84-year orbit
    "Neptune": 0.0059,   # 165-year orbit
    "Pluto": 0.0040,     # 248-year orbit
}

# Per-planet thresholds (in degrees/day) for treating a tara-graha as
# stationary (vikala) according to traditional Jyotish practice.
STATIONARY_THRESHOLDS = {
    "Mercury": 0.20,   # mean ~1.38°/day
    "Venus": 0.20,     # mean ~1.20°/day
    "Mars": 0.10,      # mean ~0.52°/day
    "Jupiter": 0.02,   # mean ~0.083°/day
    "Saturn": 0.01,    # mean ~0.034°/day
}

# Combustion thresholds (angular distance from Sun in degrees) per Laghu Parashari / BPHS.
# Mercury and Venus have tighter thresholds when retrograde (they face the Sun directly).
# Sun, Rahu, Ketu, and outer planets are not subject to combustion.
COMBUSTION_THRESHOLDS = {
    "Moon":    {"direct": 12.0, "retrograde": 12.0},
    "Mars":    {"direct": 17.0, "retrograde": 17.0},
    "Mercury": {"direct": 14.0, "retrograde": 12.0},
    "Jupiter": {"direct": 11.0, "retrograde": 11.0},
    "Venus":   {"direct": 10.0, "retrograde":  8.0},
    "Saturn":  {"direct": 15.0, "retrograde": 15.0},
}

# Ordered lists and mappings used for Vedic computations
ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

NAKSHATRA_NAMES = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]

# Sign element indices for navamsha calculation (0=Aries ... 11=Pisces)
FIRE_SIGNS = {0, 4, 8}    # Aries, Leo, Sagittarius
EARTH_SIGNS = {1, 5, 9}   # Taurus, Virgo, Capricorn
AIR_SIGNS = {2, 6, 10}    # Gemini, Libra, Aquarius
WATER_SIGNS = {3, 7, 11}  # Cancer, Scorpio, Pisces

# Geometric spans in degrees
NAKSHATRA_SPAN_DEG = 360.0 / 27.0
CHARAN_SPAN_DEG = NAKSHATRA_SPAN_DEG / 4.0  # 3°20'
