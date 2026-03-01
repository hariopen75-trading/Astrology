"""
predictor.py — South Vedic Astrology Prediction Engine
Combines chart data with the SQLite knowledge base to generate
structured life predictions across 7 domains.

Sources: Kerala Jyotisha [K], Vedic Integrated Approach [VI], Parasara [P]
"""
import sqlite3, os
import swisseph as swe
from datetime import datetime
import pytz
from vedic_data import SIGNS, PLANETS_INFO, NAKSHATRAS

DB_PATH = os.path.join(os.path.dirname(__file__), "db", "vedic_knowledge.db")

# ─────────────────────────────────────────────────────────────────────────────
# Database helper
# ─────────────────────────────────────────────────────────────────────────────
def _db_query(sql: str, params=()):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# Special Lagna Calculations
# ─────────────────────────────────────────────────────────────────────────────
def calculate_special_lagnas(chart: dict, birth_date, birth_time, lat: float, lon: float, tz_str: str) -> dict:
    """
    Compute Hora Lagna, Ghati Lagna, Sree Lagna, Arudha Lagna,
    and Chara Karakas from chart data.
    """
    from datetime import datetime, time as dtime
    import pytz

    tz = pytz.timezone(tz_str)
    dt_local = datetime.combine(birth_date, birth_time)
    dt_aware = tz.localize(dt_local)
    dt_utc = dt_aware.astimezone(pytz.utc)

    jd_birth = chart["jd"]

    # ── Sunrise JD (approximate — Sun on eastern horizon at birth location) ──
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd_noon = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, 12.0)
    sun_pos_noon, _ = swe.calc_ut(jd_noon, swe.SUN, swe.FLG_SIDEREAL)
    sun_lon_noon = sun_pos_noon[0] % 360

    # Approximate sunrise: subtract ~6h from noon
    jd_sunrise = jd_noon - 0.25  # approximate

    sun_at_sunrise, _ = swe.calc_ut(jd_sunrise, swe.SUN, swe.FLG_SIDEREAL)
    sun_lon_sunrise = sun_at_sunrise[0] % 360

    # Birth time in minutes from midnight UTC
    birth_minutes_from_midnight = dt_utc.hour * 60 + dt_utc.minute

    # Approximate sunrise in minutes from midnight (sunrise ~ 6am local = offset by timezone)
    tz_offset_hours = dt_aware.utcoffset().total_seconds() / 3600
    sunrise_local_minutes = 6 * 60  # approximate 6am local
    birth_minutes_from_sunrise = max(0, (dt_local.hour * 60 + dt_local.minute) - sunrise_local_minutes)

    # ── HORA LAGNA ──
    # Moves 1 rasi per 60 minutes (1 hora)
    hora_advance_degrees = (birth_minutes_from_sunrise / 60) * 30  # 30° per hour
    hora_lagna_lon = (sun_lon_sunrise + hora_advance_degrees) % 360
    hora_lagna_sign = int(hora_lagna_lon / 30)

    # ── GHATI LAGNA ──
    # Moves 1 rasi per 24 minutes (1 ghati)
    ghati_advance_degrees = (birth_minutes_from_sunrise / 24) * 30  # 30° per 24 min
    ghati_lagna_lon = (sun_lon_sunrise + ghati_advance_degrees) % 360
    ghati_lagna_sign = int(ghati_lagna_lon / 30)

    # ── SREE LAGNA ──
    # Based on Moon's position within its nakshatra, mapped to same fraction of zodiac
    moon_lon = chart["planets"]["Moon"]["longitude"]
    moon_nak = chart["planets"]["Moon"]["nakshatra"]
    nak_span = 360 / 27  # 13.333°
    moon_fraction_in_nak = (moon_lon % nak_span) / nak_span
    sree_lagna_advance = moon_fraction_in_nak * 360
    lagna_lon = chart["lagna_sign"] * 30 + chart["lagna_degree"]
    sree_lagna_lon = (lagna_lon + sree_lagna_advance) % 360
    sree_lagna_sign = int(sree_lagna_lon / 30)

    # ── ARUDHA LAGNA (AL1) ──
    lagna_sign = chart["lagna_sign"]
    lagna_lord_sign = chart["planets"][SIGNS[lagna_sign]["lord"]]["sign"]
    # Count from lagna to lagna lord
    count_to_lord = ((lagna_lord_sign - lagna_sign) % 12)
    if count_to_lord == 0:
        count_to_lord = 12
    # Count same from lord's position
    arudha_sign = (lagna_lord_sign + count_to_lord - 1) % 12
    # Exception: if result is 1st or 7th from original, add 10
    if arudha_sign == lagna_sign:
        arudha_sign = (lagna_sign + 9) % 12
    elif arudha_sign == (lagna_sign + 6) % 12:
        arudha_sign = (arudha_sign + 9) % 12

    # ── UPAPADA LAGNA (Arudha of 12th house) ──
    twelfth_sign = (lagna_sign + 11) % 12
    twelfth_lord_name = SIGNS[twelfth_sign]["lord"]
    twelfth_lord_sign = chart["planets"][twelfth_lord_name]["sign"]
    count_to_12th_lord = ((twelfth_lord_sign - twelfth_sign) % 12)
    if count_to_12th_lord == 0:
        count_to_12th_lord = 12
    upapada_sign = (twelfth_lord_sign + count_to_12th_lord - 1) % 12
    if upapada_sign == twelfth_sign:
        upapada_sign = (twelfth_sign + 9) % 12
    elif upapada_sign == (twelfth_sign + 6) % 12:
        upapada_sign = (upapada_sign + 9) % 12

    # ── CHARA KARAKAS ──
    # Rank planets by degree within sign (highest = AtmaKaraka)
    # Rahu uses reverse (distance from 30° instead of 0°)
    karaka_planets = ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn","Rahu"]
    karaka_names  = ["AtmaKaraka","AmatyaKaraka","BhatriKaraka","MatriKaraka",
                     "PitriKaraka","PutraKaraka","GnaatiKaraka","DaraKaraka"]

    planet_degrees = {}
    for p in karaka_planets:
        deg = chart["planets"][p]["degree"]
        if p == "Rahu":
            deg = 30 - deg  # Rahu is reverse
        planet_degrees[p] = deg

    sorted_planets = sorted(planet_degrees.keys(), key=lambda x: planet_degrees[x], reverse=True)
    chara_karakas = {karaka_names[i]: sorted_planets[i] for i in range(len(sorted_planets))}

    return {
        "hora_lagna": {"sign": hora_lagna_sign, "sign_name": SIGNS[hora_lagna_sign]["name"]},
        "ghati_lagna": {"sign": ghati_lagna_sign, "sign_name": SIGNS[ghati_lagna_sign]["name"]},
        "sree_lagna": {"sign": sree_lagna_sign, "sign_name": SIGNS[sree_lagna_sign]["name"]},
        "arudha_lagna": {"sign": arudha_sign, "sign_name": SIGNS[arudha_sign]["name"]},
        "upapada_lagna": {"sign": upapada_sign, "sign_name": SIGNS[upapada_sign]["name"]},
        "chara_karakas": chara_karakas,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Planet strength classifier
# ─────────────────────────────────────────────────────────────────────────────
def _planet_strength(planet_name: str, chart: dict) -> str:
    """Return 'strong' | 'weak' | 'neutral' based on sign placement."""
    info = PLANETS_INFO.get(planet_name, {})
    sign = chart["planets"][planet_name]["sign"]
    if sign == info.get("exaltation"):
        return "strong"
    if sign in info.get("own_sign", []):
        return "strong"
    if sign == info.get("debilitation"):
        return "weak"
    # Friendly vs enemy sign
    lord_of_sign = SIGNS[sign]["lord"]
    if lord_of_sign in info.get("friends", []):
        return "strong"
    if lord_of_sign in info.get("enemies", []):
        return "weak"
    return "neutral"


def _house_has_malefic(house: int, chart: dict) -> bool:
    malefics = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
    return any(d["house"] == house for p, d in chart["planets"].items() if p in malefics)


def _house_has_benefic(house: int, chart: dict) -> bool:
    benefics = {"Moon", "Mercury", "Jupiter", "Venus"}
    return any(d["house"] == house for p, d in chart["planets"].items() if p in benefics)


def _planets_in_house(house: int, chart: dict) -> list:
    return [p for p, d in chart["planets"].items() if d["house"] == house]


# ─────────────────────────────────────────────────────────────────────────────
# Core prediction generator
# ─────────────────────────────────────────────────────────────────────────────
def generate_predictions(chart: dict, special_lagnas: dict) -> dict:
    """
    Generate structured predictions from chart + knowledge DB.
    Returns dict with keys: general, wealth, career, marriage,
                            health, spiritual, timing, yogas_active
    """
    predictions = {
        "general":    [],
        "wealth":     [],
        "career":     [],
        "marriage":   [],
        "health":     [],
        "spiritual":  [],
        "timing":     [],
        "yogas_active": [],
        "neecha_bhanga": [],
        "disease_watch": [],
        "special_lagnas_reading": [],
        "chara_karaka_reading": [],
        "argala_reading": [],
    }

    lagna_sign = chart["lagna_sign"]
    planets    = chart["planets"]

    # ── 1. LAGNA LORD RULES ──
    lagna_lord_name = SIGNS[lagna_sign]["lord"]
    lagna_lord_house = planets[lagna_lord_name]["house"]
    lagna_lord_strength = _planet_strength(lagna_lord_name, chart)

    rows = _db_query(
        "SELECT * FROM lagna_lord_rules WHERE lagna_lord_house=? ORDER BY sentiment DESC",
        (lagna_lord_house,)
    )
    for r in rows:
        cond = r["condition"]
        # Check if condition matches
        if cond is None:
            match = True
        elif "strong" in (cond or "").lower() and lagna_lord_strength == "strong":
            match = True
        elif "weak" in (cond or "").lower() and lagna_lord_strength == "weak":
            match = True
        elif "benefic" in (cond or "").lower() and _house_has_benefic(lagna_lord_house, chart):
            match = True
        elif "malefic" in (cond or "").lower() and _house_has_malefic(lagna_lord_house, chart):
            match = True
        else:
            match = (cond is None)  # only include unconditional rules

        if match:
            entry = {
                "rule": f"Lagna lord {lagna_lord_name} in H{lagna_lord_house}",
                "text": r["effect"],
                "sentiment": r["sentiment"],
                "source": f"[{r['source']}]",
            }
            cat = r["category"]
            if cat in predictions:
                predictions[cat].append(entry)
            else:
                predictions["general"].append(entry)

    # ── 2. KEY HOUSE LORD PLACEMENTS ──
    key_lords = {
        "wealth":    [2, 11],
        "career":    [10],
        "marriage":  [7],
        "general":   [9],
        "health":    [6, 8],
    }
    for category, houses in key_lords.items():
        for lord_house in houses:
            sign_of_house = (lagna_sign + lord_house - 1) % 12
            lord_name = SIGNS[sign_of_house]["lord"]
            placed_house = planets[lord_name]["house"]
            rows = _db_query(
                "SELECT * FROM house_lord_in_house WHERE lord_of_house=? AND placed_in_house=?",
                (lord_house, placed_house)
            )
            for r in rows:
                predictions[category].append({
                    "rule": f"H{lord_house} lord {lord_name} in H{placed_house}",
                    "text": r["effect"],
                    "sentiment": r["sentiment"],
                    "source": f"[{r['source']}]",
                })

    # ── 3. YOGAS ──
    # Check active yogas from chart's detected yogas
    for yoga in chart.get("yogas", []):
        rows = _db_query("SELECT * FROM yogas WHERE name LIKE ?", (f"%{yoga['name'].split(' ')[0]}%",))
        if rows:
            r = rows[0]
            predictions["yogas_active"].append({
                "name": r["name"],
                "type": r["yoga_type"],
                "effect": r["effect"],
                "strength": r["strength"],
                "source": f"[{r['source']}]",
            })
        else:
            predictions["yogas_active"].append({
                "name": yoga["name"],
                "type": "general",
                "effect": yoga["description"],
                "strength": "moderate",
                "source": "[VI]",
            })

    # Also check DB yogas by planet positions
    # Daridra Yoga check
    if lagna_lord_strength == "weak" and lagna_lord_house in [6, 8, 12]:
        r = _db_query("SELECT * FROM yogas WHERE name='Daridra Yoga'")
        if r:
            predictions["wealth"].append({"rule": "Daridra Yoga detected", "text": r[0]["effect"], "sentiment": "negative", "source": "[K]"})

    # Kemadruma Yoga check
    moon_house = planets["Moon"]["house"]
    h_before = ((moon_house - 2) % 12) + 1
    h_after = (moon_house % 12) + 1
    planets_around_moon = _planets_in_house(h_before, chart) + _planets_in_house(h_after, chart)
    non_shadow = [p for p in planets_around_moon if p not in ("Rahu", "Ketu")]
    if not non_shadow:
        r = _db_query("SELECT * FROM yogas WHERE name='Kemadruma Yoga'")
        if r:
            predictions["general"].append({"rule": "Kemadruma Yoga present", "text": r[0]["effect"], "sentiment": "negative", "source": "[K]"})

    # ── 4. SPECIAL RULES ──
    # Prosperity rules
    if lagna_lord_strength == "strong":
        rows = _db_query("SELECT * FROM special_rules WHERE rule_type='prosperity' AND sentiment='positive' LIMIT 3")
        for r in rows:
            predictions["wealth"].append({"rule": "Prosperity rule", "text": r["effect"], "sentiment": "positive", "source": f"[{r['source']}]"})

    # Foreign settlement
    if lagna_lord_house == 12:
        rows = _db_query("SELECT * FROM special_rules WHERE rule_type='foreign'")
        for r in rows:
            predictions["general"].append({"rule": "Foreign rule", "text": r["effect"], "sentiment": r["sentiment"], "source": f"[{r['source']}]"})

    # Longevity
    rows = _db_query("SELECT * FROM special_rules WHERE rule_type='longevity' LIMIT 4")
    for r in rows:
        predictions["health"].append({"rule": "Longevity indicator", "text": r["effect"], "sentiment": r["sentiment"], "source": f"[{r['source']}]"})

    # ── 5. DISEASE WATCH ──
    afflicted_planets = {p for p in planets if _planet_strength(p, chart) == "weak"}
    for planet in afflicted_planets:
        rows = _db_query(
            "SELECT * FROM disease_yogas WHERE planets_involved LIKE ?",
            (f"%{planet}%",)
        )
        for r in rows:
            predictions["disease_watch"].append({
                "body_part": r["body_part"],
                "organ": r["organ_system"],
                "condition": r["condition"],
                "effect": r["effect"],
                "remedy": r["remedy"],
                "source": f"[{r['source']}]",
            })

    # Also check Sun, Moon, Mars specifically (key health indicators)
    for key_planet in ["Sun", "Moon", "Mars"]:
        if _planet_strength(key_planet, chart) in ["weak"]:
            rows = _db_query(
                "SELECT * FROM disease_yogas WHERE planets_involved LIKE ?",
                (f"%{key_planet}%",)
            )
            for r in rows:
                if not any(w["body_part"] == r["body_part"] for w in predictions["disease_watch"]):
                    predictions["disease_watch"].append({
                        "body_part": r["body_part"],
                        "organ": r["organ_system"],
                        "condition": r["condition"],
                        "effect": r["effect"],
                        "remedy": r["remedy"],
                        "source": f"[{r['source']}]",
                    })

    # ── 6. DASHA TIMING ──
    dasha = chart.get("dasha", {})
    current_md = dasha.get("current_mahadasha")
    current_ad = dasha.get("current_antardasha")
    if current_md:
        md_house = planets.get(current_md, {}).get("house")
        md_strength = _planet_strength(current_md, chart)
        sign_nature = ("own" if _planet_strength(current_md, chart) == "strong" else
                       "debil" if _planet_strength(current_md, chart) == "weak" else "neutral")
        rows = _db_query(
            "SELECT * FROM dasha_effects WHERE dasha_planet=? LIMIT 3",
            (current_md,)
        )
        if rows:
            r = rows[0]
            predictions["timing"].append({
                "dasha": f"{current_md} Mahadasha / {current_ad} Antardasha",
                "general": r["general_effects"],
                "wealth": r["wealth_effects"],
                "health": r["health_effects"],
                "relationship": r["relationship_effects"],
                "career": r["career_effects"],
                "source": f"[{r['source']}]",
            })
        else:
            # Generic dasha reading
            md_planet_info = PLANETS_INFO.get(current_md, {})
            predictions["timing"].append({
                "dasha": f"{current_md} Mahadasha / {current_ad} Antardasha",
                "general": f"{current_md} Mahadasha activates the significations of H{md_house}. {md_planet_info.get('description', '')}",
                "wealth": f"Wealth results depend on {current_md}'s relationship with 2nd and 11th house.",
                "health": f"Health areas: {', '.join(md_planet_info.get('body_parts', ['General health']))}",
                "relationship": f"Relationships influenced by {current_md}'s karakas: {', '.join(md_planet_info.get('karaka', [])[:3])}",
                "career": f"Career in: {', '.join(md_planet_info.get('karaka', ['chosen field'])[:3])}",
                "source": "[VI]",
            })

    # ── 7. NEECHA BHANGA CHECK ──
    debil_signs = {info["debilitation"]: planet for planet, info in PLANETS_INFO.items() if "debilitation" in info}
    for planet, pdata in planets.items():
        if pdata["sign"] in debil_signs and debil_signs[pdata["sign"]] == planet:
            # Planet is debilitated — check for cancellation
            rows = _db_query("SELECT * FROM neecha_bhanga_rules")
            # Basic check: is the debilitation sign lord in kendra?
            debil_sign_lord = SIGNS[pdata["sign"]]["lord"]
            lord_house = planets.get(debil_sign_lord, {}).get("house", 0)
            if lord_house in [1, 4, 7, 10]:
                predictions["neecha_bhanga"].append({
                    "planet": planet,
                    "sign": pdata["sign_name"],
                    "cancellation": "Neecha Bhanga Raja Yoga — debilitation lord in kendra. Native rises from adversity to great heights.",
                    "source": "[K]",
                })
            else:
                predictions["general"].append({
                    "rule": f"{planet} debilitated in {pdata['sign_name']}",
                    "text": f"{planet} is debilitated in {pdata['sign_name']} (H{pdata['house']}). Areas governed by {planet} face challenges: {', '.join(PLANETS_INFO.get(planet, {}).get('karaka', [])[:3])}.",
                    "sentiment": "negative",
                    "source": "[K]",
                })

    # ── 8. SPECIAL LAGNA READINGS ──
    sl = special_lagnas
    hl_sign  = sl.get("hora_lagna", {}).get("sign", 0)
    gl_sign  = sl.get("ghati_lagna", {}).get("sign", 0)
    srl_sign = sl.get("sree_lagna", {}).get("sign", 0)
    al_sign  = sl.get("arudha_lagna", {}).get("sign", 0)
    ul_sign  = sl.get("upapada_lagna", {}).get("sign", 0)

    # Hora Lagna — wealth
    hl_planets = [p for p, d in planets.items() if d["sign"] == hl_sign]
    rows = _db_query(
        "SELECT * FROM special_lagna_rules WHERE lagna_type='Hora' AND aspect_house=1",
    )
    for r in rows:
        if r["planet"] and r["planet"] in hl_planets:
            predictions["special_lagnas_reading"].append({
                "lagna": "Hora Lagna (Wealth)",
                "sign": SIGNS[hl_sign]["name"],
                "rule": r["condition"],
                "text": r["effect"],
                "source": f"[{r['source']}]",
            })
    if not hl_planets:
        predictions["special_lagnas_reading"].append({
            "lagna": "Hora Lagna (Wealth)",
            "sign": SIGNS[hl_sign]["name"],
            "rule": "No planets in Hora Lagna",
            "text": f"Hora Lagna in {SIGNS[hl_sign]['name']}. Ruled by {SIGNS[hl_sign]['lord']} — wealth quality determined by {SIGNS[hl_sign]['lord']}'s strength.",
            "source": "[VI]",
        })

    # Ghati Lagna — fame/power
    gl_planets = [p for p, d in planets.items() if d["sign"] == gl_sign]
    rows = _db_query("SELECT * FROM special_lagna_rules WHERE lagna_type='Ghati' AND aspect_house=1")
    for r in rows:
        if r["planet"] and r["planet"] in gl_planets:
            predictions["special_lagnas_reading"].append({
                "lagna": "Ghati Lagna (Power & Fame)",
                "sign": SIGNS[gl_sign]["name"],
                "rule": r["condition"],
                "text": r["effect"],
                "source": f"[{r['source']}]",
            })

    # Sree Lagna — prosperity
    srl_planets = [p for p, d in planets.items() if d["sign"] == srl_sign]
    rows = _db_query("SELECT * FROM special_lagna_rules WHERE lagna_type='Sree' AND aspect_house=1")
    for r in rows:
        if r["planet"] and r["planet"] in srl_planets:
            predictions["special_lagnas_reading"].append({
                "lagna": "Sree Lagna (Lakshmi / Prosperity)",
                "sign": SIGNS[srl_sign]["name"],
                "rule": r["condition"],
                "text": r["effect"],
                "source": f"[{r['source']}]",
            })

    # Arudha Lagna — public reputation
    al_planets = [p for p, d in planets.items() if d["sign"] == al_sign]
    rows = _db_query("SELECT * FROM special_lagna_rules WHERE lagna_type='Arudha' AND aspect_house=1")
    for r in rows:
        if r["planet"] and r["planet"] in al_planets:
            predictions["special_lagnas_reading"].append({
                "lagna": "Arudha Lagna (Public Image / Maya)",
                "sign": SIGNS[al_sign]["name"],
                "rule": r["condition"],
                "text": r["effect"],
                "source": f"[{r['source']}]",
            })

    # Upapada Lagna — spouse quality
    ul_planets = [p for p, d in planets.items() if d["sign"] == ul_sign]
    rows = _db_query("SELECT * FROM special_lagna_rules WHERE lagna_type='Upapada' AND aspect_house=1")
    for r in rows:
        if r["planet"] and r["planet"] in ul_planets:
            predictions["marriage"].append({
                "rule": f"Upapada Lagna in {SIGNS[ul_sign]['name']} — {r['condition']}",
                "text": r["effect"],
                "sentiment": "positive" if "Excellent" in r["effect"] or "beautiful" in r["effect"].lower() else "mixed",
                "source": f"[{r['source']}]",
            })
    if not ul_planets:
        ul_lord = SIGNS[ul_sign]["lord"]
        ul_lord_strength = _planet_strength(ul_lord, chart)
        predictions["marriage"].append({
            "rule": f"Upapada Lagna in {SIGNS[ul_sign]['name']} (lord: {ul_lord})",
            "text": f"Upapada Lagna lord {ul_lord} is {ul_lord_strength}. {'Spouse brings positive qualities.' if ul_lord_strength == 'strong' else 'Spouse may face challenges or relationship requires conscious nurturing.' if ul_lord_strength == 'weak' else 'Balanced marriage dynamics.'}",
            "sentiment": ul_lord_strength if ul_lord_strength != "neutral" else "mixed",
            "source": "[VI]",
        })

    # ── 9. CHARA KARAKA READINGS ──
    ck = sl.get("chara_karakas", {})
    for karaka_name, planet_name in ck.items():
        rows = _db_query(
            "SELECT * FROM chara_karaka_effects WHERE karaka=? AND (karaka_planet=? OR karaka_planet IS NULL)",
            (karaka_name, planet_name)
        )
        for r in rows:
            predictions["chara_karaka_reading"].append({
                "karaka": karaka_name,
                "planet": planet_name,
                "text": r["effect"],
                "category": r["category"],
                "source": f"[{r['source']}]",
            })

    # ── 10. ARGALA ANALYSIS on Lagna ──
    # Check 2nd, 4th, 11th from lagna for argala
    argala_positions = {2: "2nd (sustenance)", 4: "4th (comfort)", 11: "11th (gains)", 5: "5th (secondary)"}
    for offset, label in argala_positions.items():
        argala_house = ((lagna_sign + offset - 1) % 12) + 1
        argala_planets = _planets_in_house(offset, chart)
        if argala_planets:
            benefics = {"Moon", "Mercury", "Jupiter", "Venus"}
            ben_count = sum(1 for p in argala_planets if p in benefics)
            mal_count = len(argala_planets) - ben_count
            argala_type = "Primary" if offset != 5 else "Secondary"
            nature = "benefic" if ben_count > mal_count else "malefic" if mal_count > ben_count else "mixed"
            rows = _db_query(
                "SELECT * FROM argala_rules WHERE argala_type=? AND from_position=? AND planet_nature IN (?,?)",
                (argala_type, offset, nature, "any")
            )
            for r in rows:
                predictions["argala_reading"].append({
                    "position": label,
                    "planets": argala_planets,
                    "nature": nature,
                    "text": r["effect_on_reference"],
                    "source": f"[{r['source']}]",
                })

    # ── 11. MARRIAGE — 7th house deep analysis ──
    h7_planets = _planets_in_house(7, chart)
    venus_house = planets["Venus"]["house"]
    venus_strength = _planet_strength("Venus", chart)
    seventh_sign  = (lagna_sign + 6) % 12
    seventh_lord  = SIGNS[seventh_sign]["lord"]
    seventh_lord_strength = _planet_strength(seventh_lord, chart)

    if venus_strength == "strong":
        predictions["marriage"].append({
            "rule": "Venus strong in chart",
            "text": f"Venus in {planets['Venus']['sign_name']} (H{venus_house}) is strong — romantic life is fulfilling, spouse is charming and artistic.",
            "sentiment": "positive",
            "source": "[K]",
        })
    elif venus_strength == "weak":
        predictions["marriage"].append({
            "rule": "Venus weak in chart",
            "text": f"Venus debilitated/weak in {planets['Venus']['sign_name']} — relationship challenges, possible delays in romantic fulfillment, or health issues for spouse.",
            "sentiment": "negative",
            "source": "[K]",
        })

    # 7th lord strength
    predictions["marriage"].append({
        "rule": f"7th lord {seventh_lord} in H{planets[seventh_lord]['house']}",
        "text": f"The 7th house lord {seventh_lord} is {seventh_lord_strength} in {planets[seventh_lord]['sign_name']}. {'Marriage is auspicious and well-supported.' if seventh_lord_strength == 'strong' else 'Marriage may face challenges or delays.' if seventh_lord_strength == 'weak' else 'Balanced marriage outlook.'}",
        "sentiment": "positive" if seventh_lord_strength == "strong" else "negative" if seventh_lord_strength == "weak" else "neutral",
        "source": "[K]",
    })

    # ── 12. CAREER — 10th house deep analysis ──
    tenth_sign = (lagna_sign + 9) % 12
    tenth_lord = SIGNS[tenth_sign]["lord"]
    tenth_lord_house = planets[tenth_lord]["house"]
    tenth_lord_strength = _planet_strength(tenth_lord, chart)
    sun_house = planets["Sun"]["house"]

    predictions["career"].append({
        "rule": f"10th lord {tenth_lord} in H{tenth_lord_house}",
        "text": f"Career is governed by {tenth_lord} (H{tenth_lord_house}, {planets[tenth_lord]['sign_name']}). {'Strong professional foundation — career in {}'.format(', '.join(PLANETS_INFO.get(tenth_lord, {}).get('karaka', ['chosen field'])[:3])) if tenth_lord_strength == 'strong' else 'Career requires sustained effort — delays but eventual success.' if tenth_lord_strength == 'weak' else 'Moderate career development through consistent work.'}",
        "sentiment": "positive" if tenth_lord_strength == "strong" else "mixed",
        "source": "[K]",
    })

    # Sun in 10th — government/authority careers
    if planets["Sun"]["house"] == 10:
        predictions["career"].append({
            "rule": "Sun in 10th house",
            "text": "Sun in 10th — Government career, leadership, and public authority are strongly indicated. Career defines the native's identity.",
            "sentiment": "positive",
            "source": "[K]",
        })

    # ── 13. WEALTH — 2nd and 11th analysis ──
    second_sign = (lagna_sign + 1) % 12
    second_lord = SIGNS[second_sign]["lord"]
    second_lord_strength = _planet_strength(second_lord, chart)
    eleventh_sign = (lagna_sign + 10) % 12
    eleventh_lord = SIGNS[eleventh_sign]["lord"]
    eleventh_lord_strength = _planet_strength(eleventh_lord, chart)
    jupiter_house = planets["Jupiter"]["house"]
    jupiter_strength = _planet_strength("Jupiter", chart)

    if jupiter_strength == "strong":
        predictions["wealth"].append({
            "rule": "Jupiter strong",
            "text": f"Jupiter strong in {planets['Jupiter']['sign_name']} (H{jupiter_house}) — Kubera blesses wealth. Financial expansion is natural and sustained.",
            "sentiment": "positive",
            "source": "[K]",
        })

    predictions["wealth"].append({
        "rule": f"2nd lord {second_lord} ({second_lord_strength}), 11th lord {eleventh_lord} ({eleventh_lord_strength})",
        "text": f"Wealth axis: 2nd lord {second_lord} is {second_lord_strength}, 11th lord {eleventh_lord} is {eleventh_lord_strength}. {'Both strong — excellent wealth and income potential.' if second_lord_strength == 'strong' and eleventh_lord_strength == 'strong' else 'Both weak — financial challenges throughout life.' if second_lord_strength == 'weak' and eleventh_lord_strength == 'weak' else 'Mixed wealth — income and accumulation require consistent effort.'}",
        "sentiment": "positive" if second_lord_strength == "strong" and eleventh_lord_strength == "strong" else "negative" if second_lord_strength == "weak" and eleventh_lord_strength == "weak" else "neutral",
        "source": "[K]",
    })

    # ── 14. SPIRITUAL — 12th house analysis ──
    twelfth_planets = _planets_in_house(12, chart)
    ketu_house = planets["Ketu"]["house"]
    jupiter_12 = planets["Jupiter"]["house"] == 12

    if ketu_house == 12:
        predictions["spiritual"].append({
            "rule": "Ketu in 12th",
            "text": "Ketu in 12th — strongest moksha indicator. Natural yogi, past-life renunciate, born seeker of liberation. Meditation and solitary spiritual practice are deeply fulfilling.",
            "sentiment": "positive",
            "source": "[VI]",
        })
    if jupiter_12:
        predictions["spiritual"].append({
            "rule": "Jupiter in 12th",
            "text": "Jupiter in 12th — wisdom expressed in solitude, foreign lands, or spiritual retreat. Exceptional spiritual teacher or seeker. Ashram or temple life resonates deeply.",
            "sentiment": "positive",
            "source": "[VI]",
        })

    ninth_sign = (lagna_sign + 8) % 12
    ninth_lord = SIGNS[ninth_sign]["lord"]
    ninth_lord_strength = _planet_strength(ninth_lord, chart)
    if ninth_lord_strength == "strong":
        predictions["spiritual"].append({
            "rule": f"9th lord {ninth_lord} strong",
            "text": f"9th lord {ninth_lord} is strong in {planets[ninth_lord]['sign_name']} — dharmic path is clear, religious and philosophical life is fulfilling. Good karma from past lives supports spiritual growth.",
            "sentiment": "positive",
            "source": "[K]",
        })

    # ── Deduplicate all prediction lists ──
    for key in predictions:
        if isinstance(predictions[key], list):
            seen = set()
            deduped = []
            for item in predictions[key]:
                text = item.get("text", item.get("effect", "")) if isinstance(item, dict) else str(item)
                if text not in seen:
                    seen.add(text)
                    deduped.append(item)
            predictions[key] = deduped

    return predictions


# ─────────────────────────────────────────────────────────────────────────────
# Summary paragraph generator
# ─────────────────────────────────────────────────────────────────────────────
def generate_summary(chart: dict, predictions: dict, special_lagnas: dict) -> str:
    """Generate a concise overall prediction summary paragraph."""
    lagna = chart["lagna_sign_name"]
    lagna_lord = SIGNS[chart["lagna_sign"]]["lord"]
    ll_house = chart["planets"][lagna_lord]["house"]
    moon_sign = chart["planets"]["Moon"]["sign_name"]
    moon_nak = chart["planets"]["Moon"]["nakshatra_name"]
    dasha = chart["dasha"]
    current_md = dasha.get("current_mahadasha", "unknown")
    current_ad = dasha.get("current_antardasha", "unknown")
    ck = special_lagnas.get("chara_karakas", {})
    ak = ck.get("AtmaKaraka", "unknown")
    dk = ck.get("DaraKaraka", "unknown")

    positive_yogas = [y["name"] for y in predictions.get("yogas_active", []) if y.get("type") in ["raja", "dhana"]]
    neecha = [n["planet"] for n in predictions.get("neecha_bhanga", [])]

    summary = f"""**Lagna:** {lagna} | **Moon:** {moon_sign} ({moon_nak} Nakshatra) | **Current Dasha:** {current_md}/{current_ad}

**AtmaKaraka (Soul Planet):** {ak} — This planet defines the soul's primary purpose in this lifetime.
**DaraKaraka (Spouse Significator):** {dk} — This planet reveals the nature of your life partner.

The lagna lord **{lagna_lord}** placed in the **{ll_house}th house** shapes the primary direction of this life.
"""
    if positive_yogas:
        summary += f"\n**Active Raja/Dhana Yogas:** {', '.join(positive_yogas)} — These special combinations elevate life quality and bring recognition."

    if neecha:
        summary += f"\n**Neecha Bhanga (Cancellation of Debilitation):** {', '.join(neecha)} — Debilitation is cancelled, transforming apparent weakness into remarkable strength."

    wealth_pos = [w for w in predictions.get("wealth", []) if w.get("sentiment") == "positive"]
    if wealth_pos:
        summary += f"\n\n**Wealth Outlook:** {wealth_pos[0]['text'][:120]}..."

    career_pos = [c for c in predictions.get("career", []) if c.get("sentiment") in ["positive", "mixed"]]
    if career_pos:
        summary += f"\n**Career:** {career_pos[0]['text'][:120]}..."

    return summary
