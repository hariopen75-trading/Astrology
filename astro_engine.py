# astro_engine.py — Vedic Birth Chart Calculation Engine
# Uses Swiss Ephemeris (pyswisseph) with Lahiri ayanamsha + Whole Sign Houses

import swisseph as swe
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim
import pytz
from vedic_data import (
    DASHA_ORDER, DASHA_PERIODS, NAKSHATRA_LORD,
    NAKSHATRAS, SIGNS, ASPECTS, CONJUNCTIONS
)

# ─────────────────────────────────────────────
# Swiss Ephemeris planet IDs
# ─────────────────────────────────────────────
SWE_PLANETS = {
    "Sun":     swe.SUN,
    "Moon":    swe.MOON,
    "Mars":    swe.MARS,
    "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER,
    "Venus":   swe.VENUS,
    "Saturn":  swe.SATURN,
    "Rahu":    swe.TRUE_NODE,
}

PLANET_SYMBOLS = {
    "Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me",
    "Jupiter": "Ju", "Venus": "Ve", "Saturn": "Sa", "Rahu": "Ra", "Ketu": "Ke",
}

# ─────────────────────────────────────────────
# Geocoding
# ─────────────────────────────────────────────
_geolocator = Nominatim(user_agent="vedic_astro_agent_v1", timeout=10)

def get_coordinates(place_name: str):
    """Return (lat, lon, display_name) for a city/place string."""
    try:
        loc = _geolocator.geocode(place_name)
        if loc:
            return loc.latitude, loc.longitude, loc.address
    except Exception:
        pass
    return None, None, None

# ─────────────────────────────────────────────
# Core calculation
# ─────────────────────────────────────────────
def calculate_chart(birth_date: datetime.date, birth_time: datetime.time,
                    lat: float, lon: float, tz_str: str) -> dict:
    """
    Calculate a complete Vedic birth chart.

    Returns a dict with:
      lagna_sign (0-11), lagna_degree, planets (dict), jd,
      conjunctions, aspects, yogas_detected
    """
    # Convert local birth datetime to UTC
    tz = pytz.timezone(tz_str)
    dt_local = datetime.combine(birth_date, birth_time)
    dt_aware = tz.localize(dt_local)
    dt_utc = dt_aware.astimezone(pytz.utc)

    # Julian Day Number (UT)
    jd = swe.julday(
        dt_utc.year, dt_utc.month, dt_utc.day,
        dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
    )

    # Set Lahiri ayanamsha (standard for South Indian Vedic)
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    ayanamsha = swe.get_ayanamsa(jd)

    # Ascendant — use Placidus to get tropical ASC then subtract ayanamsha
    houses_tropical, ascmc = swe.houses(jd, lat, lon, b'P')
    asc_tropical = ascmc[0]
    asc_sidereal = (asc_tropical - ayanamsha) % 360

    lagna_sign = int(asc_sidereal / 30)      # 0 = Aries … 11 = Pisces
    lagna_degree = asc_sidereal % 30

    # Calculate all 9 planets (sidereal)
    planets = {}
    for name, pid in SWE_PLANETS.items():
        result, _ = swe.calc_ut(jd, pid, swe.FLG_SIDEREAL)
        lon_sid = result[0] % 360
        speed = result[3]

        sign_num = int(lon_sid / 30)
        degree = lon_sid % 30
        # Whole Sign house: how many signs from lagna
        house_num = ((sign_num - lagna_sign) % 12) + 1

        nak_idx = int(lon_sid * 27 / 360)
        nak_pada = int(((lon_sid * 27 / 360) - nak_idx) * 4) + 1

        planets[name] = {
            "longitude": round(lon_sid, 4),
            "sign": sign_num,
            "sign_name": SIGNS[sign_num]["name"],
            "degree": round(degree, 2),
            "house": house_num,
            "nakshatra": nak_idx,
            "nakshatra_name": NAKSHATRAS[nak_idx]["name"],
            "nakshatra_lord": NAKSHATRAS[nak_idx]["lord"],
            "pada": nak_pada,
            "retrograde": speed < 0,
            "symbol": PLANET_SYMBOLS[name],
        }

    # Ketu = Rahu + 180°
    rahu_lon = planets["Rahu"]["longitude"]
    ketu_lon = (rahu_lon + 180) % 360
    k_sign = int(ketu_lon / 30)
    k_deg = ketu_lon % 30
    k_house = ((k_sign - lagna_sign) % 12) + 1
    k_nak = int(ketu_lon * 27 / 360)
    planets["Ketu"] = {
        "longitude": round(ketu_lon, 4),
        "sign": k_sign,
        "sign_name": SIGNS[k_sign]["name"],
        "degree": round(k_deg, 2),
        "house": k_house,
        "nakshatra": k_nak,
        "nakshatra_name": NAKSHATRAS[k_nak]["name"],
        "nakshatra_lord": NAKSHATRAS[k_nak]["lord"],
        "pada": int(((ketu_lon * 27 / 360) - k_nak) * 4) + 1,
        "retrograde": False,
        "symbol": "Ke",
    }

    # Detect conjunctions (planets in same house)
    conjunctions_found = _detect_conjunctions(planets)

    # Detect aspects
    aspects_found = _detect_aspects(planets)

    # Calculate Vimshottari Dasha
    dasha_info = _calculate_dasha(planets["Moon"]["nakshatra"],
                                  planets["Moon"]["degree"],
                                  dt_utc)

    # Detect basic yogas
    yogas = _detect_yogas(planets, lagna_sign)

    return {
        "lagna_sign": lagna_sign,
        "lagna_sign_name": SIGNS[lagna_sign]["name"],
        "lagna_degree": round(lagna_degree, 2),
        "planets": planets,
        "jd": jd,
        "lat": lat,
        "lon": lon,
        "ayanamsha": round(ayanamsha, 4),
        "conjunctions": conjunctions_found,
        "aspects": aspects_found,
        "dasha": dasha_info,
        "yogas": yogas,
    }

# ─────────────────────────────────────────────
# Conjunction detection
# ─────────────────────────────────────────────
def _detect_conjunctions(planets: dict) -> list:
    """Find all planets sharing the same house."""
    house_groups = {}
    for name, data in planets.items():
        h = data["house"]
        house_groups.setdefault(h, []).append(name)

    results = []
    for house, planet_list in house_groups.items():
        if len(planet_list) >= 2:
            for i in range(len(planet_list)):
                for j in range(i + 1, len(planet_list)):
                    p1, p2 = planet_list[i], planet_list[j]
                    key = frozenset([p1, p2])
                    conj_data = CONJUNCTIONS.get(key, {})
                    results.append({
                        "planets": [p1, p2],
                        "house": house,
                        "name": conj_data.get("name", f"{p1}-{p2} Conjunction"),
                        "behavior": conj_data.get("behavior", "Combined energy of both planets in this house."),
                        "positive": conj_data.get("positive", []),
                        "challenges": conj_data.get("challenges", []),
                        "career": conj_data.get("career", ""),
                        "nature": conj_data.get("nature", "Mixed"),
                    })
    return results

# ─────────────────────────────────────────────
# Aspect detection
# ─────────────────────────────────────────────
def _detect_aspects(planets: dict) -> list:
    """Determine which planets aspect which houses/signs."""
    results = []
    for planet_name, data in planets.items():
        house = data["house"]
        full_aspects = ASPECTS.get(planet_name, {}).get("full", [7])
        for offset in full_aspects:
            aspected_house = ((house - 1 + offset) % 12) + 1
            # Find planets in aspected house
            aspected_planets = [
                p for p, d in planets.items()
                if d["house"] == aspected_house and p != planet_name
            ]
            results.append({
                "from_planet": planet_name,
                "from_house": house,
                "aspected_house": aspected_house,
                "aspected_planets": aspected_planets,
                "aspect_type": "Full (Drishti)",
            })
    return results

# ─────────────────────────────────────────────
# Vimshottari Dasha calculation
# ─────────────────────────────────────────────
def _calculate_dasha(moon_nak: int, moon_deg_in_nak: float, birth_utc: datetime) -> dict:
    """Calculate current Mahadasha and Antardasha."""
    nak_lord = NAKSHATRA_LORD[moon_nak]
    total_period = DASHA_PERIODS[nak_lord]  # years

    # Nakshatra span = 360/27 = 13.333...° total, each pada = 3.333°
    # Moon degree within nakshatra (0–13.333°)
    nak_span = 360 / 27  # 13.3333...
    # How far through the nakshatra is the Moon (0.0 to 1.0)
    moon_lon_within_nak = (moon_deg_in_nak % nak_span)
    fraction_elapsed = moon_lon_within_nak / nak_span
    years_elapsed = total_period * fraction_elapsed
    years_remaining = total_period - years_elapsed

    # Build the dasha sequence starting from nak_lord
    start_idx = DASHA_ORDER.index(nak_lord)
    sequence = DASHA_ORDER[start_idx:] + DASHA_ORDER[:start_idx]

    # Start date of first dasha (birth - years_elapsed)
    dasha_start = birth_utc - timedelta(days=years_elapsed * 365.25)

    dashas = []
    current_date = datetime.now(pytz.utc)
    current_dasha = None
    current_antardasha = None

    cursor = dasha_start
    for maha_planet in sequence:
        maha_years = DASHA_PERIODS[maha_planet]
        maha_end = cursor + timedelta(days=maha_years * 365.25)

        is_current = cursor <= current_date < maha_end
        if is_current:
            current_dasha = maha_planet

        # Antardasha within this mahadasha
        antars = []
        ant_cursor = cursor
        ant_start_idx = DASHA_ORDER.index(maha_planet)
        ant_sequence = DASHA_ORDER[ant_start_idx:] + DASHA_ORDER[:ant_start_idx]
        for antar_planet in ant_sequence:
            antar_years = (DASHA_PERIODS[antar_planet] / 120) * maha_years
            antar_end = ant_cursor + timedelta(days=antar_years * 365.25)
            if is_current and ant_cursor <= current_date < antar_end:
                current_antardasha = antar_planet
            antars.append({
                "planet": antar_planet,
                "start": ant_cursor.strftime("%b %Y"),
                "end": antar_end.strftime("%b %Y"),
                "active": is_current and ant_cursor <= current_date < antar_end,
            })
            ant_cursor = antar_end

        dashas.append({
            "planet": maha_planet,
            "years": maha_years,
            "start": cursor.strftime("%b %Y"),
            "end": maha_end.strftime("%b %Y"),
            "active": is_current,
            "antardasha": antars,
        })
        cursor = maha_end

    return {
        "current_mahadasha": current_dasha,
        "current_antardasha": current_antardasha,
        "sequence": dashas,
    }

# ─────────────────────────────────────────────
# Basic Yoga detection
# ─────────────────────────────────────────────
def _detect_yogas(planets: dict, lagna_sign: int) -> list:
    """Detect major yogas in the chart."""
    yogas = []

    def house_of(planet):
        return planets[planet]["house"]

    def sign_of(planet):
        return planets[planet]["sign"]

    # Gaja Kesari Yoga: Jupiter in kendra (1,4,7,10) from Moon
    moon_house = house_of("Moon")
    jup_house = house_of("Jupiter")
    diff = ((jup_house - moon_house) % 12) + 1
    if diff in [1, 4, 7, 10]:
        yogas.append({
            "name": "Gaja Kesari Yoga",
            "description": "Jupiter in kendra from Moon — wisdom, wealth, fame, and respected leadership.",
            "planets": ["Moon", "Jupiter"],
        })

    # Budhaditya Yoga: Sun and Mercury in same house
    if house_of("Sun") == house_of("Mercury"):
        yogas.append({
            "name": "Budhaditya Yoga",
            "description": "Sun conjunct Mercury — sharp intelligence, eloquent speech, and government favor.",
            "planets": ["Sun", "Mercury"],
        })

    # Chandra-Mangal Yoga: Moon and Mars conjunct
    if house_of("Moon") == house_of("Mars"):
        yogas.append({
            "name": "Chandra-Mangal Yoga",
            "description": "Moon conjunct Mars — wealth through bold emotional intelligence and business.",
            "planets": ["Moon", "Mars"],
        })

    # Pancha Mahapurusha Yogas
    kendra_houses = [1, 4, 7, 10]
    own_signs = {
        "Mars":    [0, 7],
        "Mercury": [2, 5],
        "Jupiter": [8, 11],
        "Venus":   [1, 6],
        "Saturn":  [9, 10],
    }
    exalt_signs = {
        "Mars": 9, "Mercury": 5, "Jupiter": 3, "Venus": 11, "Saturn": 6,
    }
    yoga_names = {
        "Mars": "Ruchaka Yoga", "Mercury": "Bhadra Yoga",
        "Jupiter": "Hamsa Yoga", "Venus": "Malavya Yoga", "Saturn": "Shasha Yoga",
    }
    for planet in ["Mars", "Mercury", "Jupiter", "Venus", "Saturn"]:
        h = house_of(planet)
        s = sign_of(planet)
        in_own = s in own_signs.get(planet, [])
        in_exalt = s == exalt_signs.get(planet)
        if h in kendra_houses and (in_own or in_exalt):
            yogas.append({
                "name": yoga_names[planet],
                "description": f"{planet} in kendra in {'own' if in_own else 'exaltation'} sign — Pancha Mahapurusha Yoga giving greatness in {planet}'s domain.",
                "planets": [planet],
            })

    # Lakshmi Yoga: Venus strong (own/exalt) and 9th lord in kendra/trikona
    venus_sign = sign_of("Venus")
    if venus_sign in [1, 6, 11]:  # own or exalted
        yogas.append({
            "name": "Lakshmi Yoga (partial)",
            "description": "Venus in own/exaltation sign — blessings of wealth, beauty, and prosperity.",
            "planets": ["Venus"],
        })

    # Adhi Yoga: Benefics in 6,7,8 from Moon
    benefics = ["Mercury", "Venus", "Jupiter"]
    from_moon = {((house_of(p) - moon_house) % 12) + 1 for p in benefics}
    if {6, 7, 8}.issubset(from_moon) or len(from_moon & {6, 7, 8}) >= 2:
        yogas.append({
            "name": "Adhi Yoga",
            "description": "Benefics in 6th/7th/8th from Moon — leadership, prosperity, and good health.",
            "planets": benefics,
        })

    return yogas

# ─────────────────────────────────────────────
# Compatibility analysis (basic)
# ─────────────────────────────────────────────
def compare_charts(chart1: dict, chart2: dict) -> dict:
    """Basic compatibility comparison between two charts."""
    results = {}

    # Moon sign compatibility (Rashi)
    m1_sign = chart1["planets"]["Moon"]["sign"]
    m2_sign = chart2["planets"]["Moon"]["sign"]
    moon_diff = abs(m1_sign - m2_sign)
    if moon_diff > 6:
        moon_diff = 12 - moon_diff

    moon_compat = {
        0: ("Excellent", "Same Moon sign — deep emotional understanding and shared instincts."),
        1: ("Good", "Adjacent Moon signs — comfortable emotional flow with some adjustments."),
        2: ("Fair", "Two signs apart — different emotional rhythms but workable."),
        3: ("Neutral", "Kona relationship — philosophical compatibility but emotional differences."),
        4: ("Challenging", "Four signs apart — friction in emotional needs."),
        5: ("Difficult", "Five signs apart — very different emotional worlds."),
        6: ("Opposite", "Opposite Moon signs — complementary but requires deep understanding."),
    }
    moon_c = moon_compat.get(moon_diff, ("Neutral", ""))
    results["moon_compatibility"] = {
        "person1_moon": SIGNS[m1_sign]["name"],
        "person2_moon": SIGNS[m2_sign]["name"],
        "rating": moon_c[0],
        "description": moon_c[1],
    }

    # Lagna compatibility
    l1 = chart1["lagna_sign"]
    l2 = chart2["lagna_sign"]
    lagna_diff = abs(l1 - l2)
    if lagna_diff > 6:
        lagna_diff = 12 - lagna_diff
    lagna_ratings = {0: "Excellent", 1: "Good", 2: "Good", 3: "Fair",
                     4: "Challenging", 5: "Difficult", 6: "Opposite/Complementary"}
    results["lagna_compatibility"] = {
        "person1_lagna": SIGNS[l1]["name"],
        "person2_lagna": SIGNS[l2]["name"],
        "rating": lagna_ratings.get(lagna_diff, "Neutral"),
    }

    # Shared houses — planets of one chart in key houses of other
    shared = []
    p2_signs = {d["sign"] for d in chart2["planets"].values()}
    for planet, data in chart1["planets"].items():
        if data["sign"] in p2_signs:
            matching = [p for p, d in chart2["planets"].items() if d["sign"] == data["sign"]]
            shared.append({
                "chart1_planet": planet,
                "chart2_planets": matching,
                "sign": SIGNS[data["sign"]]["name"],
                "note": "Planets share the same sign — strong karmic connection in this area.",
            })
    results["shared_energies"] = shared

    # Venus-Mars compatibility
    v1 = chart1["planets"]["Venus"]["sign"]
    m2_mars = chart2["planets"]["Mars"]["sign"]
    v2 = chart2["planets"]["Venus"]["sign"]
    m1_mars = chart1["planets"]["Mars"]["sign"]
    vm_note = []
    if abs(v1 - m2_mars) <= 1 or abs(v1 - m2_mars) >= 11:
        vm_note.append("Person 1's Venus aligns with Person 2's Mars — strong romantic attraction.")
    if abs(v2 - m1_mars) <= 1 or abs(v2 - m1_mars) >= 11:
        vm_note.append("Person 2's Venus aligns with Person 1's Mars — mutual passion and desire.")
    results["venus_mars_attraction"] = vm_note or ["Venus-Mars positions are in different zones — attraction requires conscious effort."]

    # Overall score (simple heuristic)
    score_map = {"Excellent": 5, "Good": 4, "Fair": 3, "Neutral": 2, "Challenging": 1, "Difficult": 0, "Opposite/Complementary": 3}
    moon_score = score_map.get(results["moon_compatibility"]["rating"], 2)
    lagna_score = score_map.get(results["lagna_compatibility"]["rating"], 2)
    shared_score = min(len(shared), 5)
    vm_score = len(vm_note) * 2
    total = moon_score + lagna_score + shared_score + vm_score
    max_score = 5 + 5 + 5 + 4
    pct = int((total / max_score) * 100)
    results["overall_score"] = min(pct, 100)
    results["overall_label"] = (
        "Excellent" if pct >= 75 else
        "Good" if pct >= 55 else
        "Fair" if pct >= 40 else
        "Needs Work"
    )

    return results
