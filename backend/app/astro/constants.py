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
}

HOUSE_CODES = {"WHOLE_SIGN": "W", "EQUAL": "E", "PLACIDUS": "P"}

# Swiss Ephemeris calculation flags
SEFLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_SIDEREAL

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
PADA_SPAN_DEG = NAKSHATRA_SPAN_DEG / 4.0  # 3°20'
