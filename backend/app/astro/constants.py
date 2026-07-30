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

# Panchang constants (English canonical names — frontend translates)
TITHI_NAMES = [
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi",
    "Saptami", "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi",
    "Trayodashi", "Chaturdashi", "Purnima", "Pratipada", "Dwitiya", "Tritiya",
    "Chaturthi", "Panchami", "Shashthi", "Saptami", "Ashtami", "Navami",
    "Dashami", "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Amavasya",
]

YOGA_NAMES = [
    "Vishkumbha", "Priti", "Ayushman", "Saubhagya", "Shobhana", "Atiganda",
    "Sukarma", "Dhriti", "Shula", "Ganda", "Vriddhi", "Dhruva", "Vyaghata",
    "Harshana", "Vajra", "Siddhi", "Vyatipata", "Variyan", "Parigha", "Shiva",
    "Siddha", "Sadhya", "Shubha", "Shukla", "Brahma", "Indra", "Vaidhriti",
]

LUNAR_MONTH_NAMES = [
    "Chaitra", "Vaishakha", "Jyeshtha", "Ashadha", "Shravana", "Bhadrapada",
    "Ashwin", "Kartika", "Margashirsha", "Pausha", "Magha", "Phalguna",
]

MOVABLE_KARANA_NAMES = [
    "Bava", "Balava", "Kaulava", "Taitila", "Garaja", "Vanija", "Vishti",
]

FIXED_KARANA_BY_SLOT = {
    0: "Kimstughna",
    57: "Shakuni",
    58: "Chatushpada",
    59: "Naga",
}

KARANA_TYPE_INDEX = {
    "Kimstughna": 1,
    "Bava": 2,
    "Balava": 3,
    "Kaulava": 4,
    "Taitila": 5,
    "Garaja": 6,
    "Vanija": 7,
    "Vishti": 8,
    "Shakuni": 9,
    "Chatushpada": 10,
    "Naga": 11,
}

VAARA_BY_PYTHON_WEEKDAY = {
    6: ("Ravivaara", 1),
    0: ("Somavaara", 2),
    1: ("Mangalavaara", 3),
    2: ("Budhavaara", 4),
    3: ("Guruvaaara", 5),
    4: ("Shukravaara", 6),
    5: ("Shanivaaara", 7),
}

SYNODIC_MONTH_DAYS = 29.53059
YOGAS_PER_CYCLE = 27
YOGA_SPAN_DEG = 360.0 / YOGAS_PER_CYCLE
