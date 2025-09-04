import swisseph as swe
from datetime import datetime
from .constants import PLANETS, AYANAMSHA, HOUSE_CODES, SEFLAGS
from .utils import norm360, sign_index, house_from_sign

def init_ephemeris(ephe_path: str, ayanamsha_key: str):
    """Initialize Swiss Ephemeris with path and ayanamsha"""
    swe.set_ephe_path(ephe_path)
    swe.set_sid_mode(AYANAMSHA[ayanamsha_key])

def julian_day_utc(dt_utc: datetime) -> float:
    """Convert UTC datetime to Julian Day"""
    ut = dt_utc.hour + dt_utc.minute/60 + dt_utc.second/3600 + dt_utc.microsecond/3.6e9
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, ut)

def ascendant_and_houses(jd_ut: float, lat: float, lon: float, houseSystem: str):
    """Calculate ascendant and house cusps"""
    hcode = HOUSE_CODES[houseSystem]
    if hcode == "W":
        # Use Placidus internally just to get ASC, then replace cusps with whole sign bins.
        _, ascmc, _ = swe.houses_ex(jd_ut, lat, lon, b'P', SEFLAGS)
        asc = norm360(ascmc[swe.SE_ASC])
        return asc, None  # cusps computed later if asked
    else:
        cusps, ascmc, _ = swe.houses_ex(jd_ut, lat, lon, hcode.encode(), SEFLAGS)
        asc = norm360(ascmc[swe.SE_ASC])
        return asc, [norm360(c) for c in cusps[1:13]]

def compute_planets(jd_ut: float, nodeType: str):
    """Compute planetary positions and speeds"""
    out = []
    # Rahu (node)
    node_body = swe.MEAN_NODE if nodeType == "MEAN" else swe.TRUE_NODE
    # Precompute node
    rahu_long, _, _, rahu_speed = swe.calc_ut(jd_ut, node_body, SEFLAGS)
    rahu_long = norm360(rahu_long)

    for name, body in PLANETS:
        if name == "Rahu":
            lng, spd = rahu_long, rahu_speed
        elif name == "Ketu":
            lng = norm360(rahu_long + 180.0)
            spd = -rahu_speed
        else:
            lng, _, _, spd = swe.calc_ut(jd_ut, body, SEFLAGS)
            lng = norm360(lng)
        out.append({
            "planet": name,
            "longitude": lng,
            "speed": spd,
            "retrograde": spd < 0
        })
    return out

def compute_whole_sign_cusps(asc_sign: int):
    """Compute whole sign house cusps"""
    return [norm360(asc_sign * 30 + i * 30) for i in range(12)]
