# app.py — South Vedic Astrology Agent (Streamlit)
# Run: streamlit run app.py

import streamlit as st
import pandas as pd
from datetime import date, time
import pytz

from astro_engine import calculate_chart, get_coordinates, compare_charts
from chart_renderer import render_south_indian_chart, render_planet_table
from predictor import calculate_special_lagnas, generate_predictions, generate_summary
from vedic_data import (
    PLANET_IN_HOUSE, CONJUNCTIONS, PLANETS_INFO, HOUSES,
    NAKSHATRAS, RAJ_YOGAS, DASHA_PERIODS, SIGNS,
)

# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="South Vedic Astrology Agent",
    page_icon="🪐",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header { font-size:2.2rem; font-weight:700; color:#B8860B; text-align:center; margin-bottom:0.2rem; }
    .sub-header  { font-size:1rem;  color:#888; text-align:center; margin-bottom:1.5rem; }
    .planet-card     { background:#FFFDE7; border-left:4px solid #DAA520; border-radius:6px; padding:12px 16px; margin:8px 0; }
    .yoga-card        { background:#E8F5E9; border-left:4px solid #388E3C; border-radius:6px; padding:10px 14px; margin:6px 0; }
    .conjunction-card { background:#E3F2FD; border-left:4px solid #1976D2; border-radius:6px; padding:10px 14px; margin:6px 0; }
    .dasha-active     { background:#FFF9C4; border:2px solid #F9A825; border-radius:6px; padding:10px 14px; margin:6px 0; font-weight:bold; }
    .section-title    { font-size:1.2rem; font-weight:600; color:#5D4037; border-bottom:2px solid #DAA520; padding-bottom:4px; margin:16px 0 10px 0; }
</style>
""", unsafe_allow_html=True)

COMMON_TZ = [
    "Asia/Kolkata", "America/New_York", "America/Los_Angeles",
    "America/Chicago", "Europe/London", "Europe/Paris", "Asia/Singapore",
    "Asia/Dubai", "Asia/Tokyo", "Australia/Sydney", "Pacific/Auckland",
]

# ─────────────────────────────────────────────
# HELPER FUNCTIONS  (defined before use)
# ─────────────────────────────────────────────

def birth_input_form(prefix: str):
    col1, col2 = st.columns(2)
    with col1:
        name       = st.text_input("Name", key=f"{prefix}_name", placeholder="e.g. Arjun Kumar")
        birth_date = st.date_input("Birth Date", value=date(1990, 1, 1),
                                   min_value=date(1900, 1, 1), max_value=date(2024, 12, 31),
                                   key=f"{prefix}_date")
        birth_time_val = st.time_input("Birth Time", value=time(6, 0), key=f"{prefix}_time")
    with col2:
        birth_place = st.text_input("Birth Place", key=f"{prefix}_place",
                                    placeholder="e.g. Chennai, India")
        tz_choice   = st.selectbox("Timezone", options=COMMON_TZ + sorted(pytz.all_timezones),
                                   index=0, key=f"{prefix}_tz")
    return name, birth_date, birth_time_val, birth_place, tz_choice


def do_calculate(name, birth_date, birth_time_val, birth_place, tz_choice):
    if not birth_place.strip():
        st.error("Please enter a birth place.")
        return None
    with st.spinner(f"Locating {birth_place}..."):
        lat, lon, addr = get_coordinates(birth_place)
    if lat is None:
        st.error(f"Could not find coordinates for '{birth_place}'. Try a more specific city name.")
        return None
    st.success(f"📍 {addr}")
    with st.spinner("Calculating chart..."):
        chart = calculate_chart(birth_date, birth_time_val, lat, lon, tz_choice)
    chart["_name"]        = name
    chart["_birth_place"] = addr
    chart["_birth_date"]  = birth_date
    chart["_birth_time"]  = birth_time_val
    chart["_tz"]          = tz_choice
    return chart


def _display_dasha(dasha: dict):
    md = dasha.get("current_mahadasha", "—")
    ad = dasha.get("current_antardasha", "—")
    st.markdown(f"""<div class="dasha-active">
        🔴 Current Mahadasha: <b>{md}</b> &nbsp;|&nbsp; Antardasha: <b>{ad}</b>
    </div>""", unsafe_allow_html=True)
    with st.expander("View full Dasha timeline"):
        for maha in dasha["sequence"]:
            label = f"**🔴 {maha['planet']}**" if maha["active"] else maha["planet"]
            st.markdown(f"{label} ({maha['start']} → {maha['end']}, {maha['years']} yrs)")
            if maha["active"]:
                for antar in maha["antardasha"]:
                    marker = "▶ **" if antar["active"] else "&nbsp;&nbsp;&nbsp;"
                    end_m  = "**" if antar["active"] else ""
                    st.markdown(f"&nbsp;&nbsp;&nbsp;{marker}{antar['planet']}{end_m}: "
                                f"{antar['start']} → {antar['end']}")


def _sentiment_color(s: str) -> str:
    return {"positive": "#2E7D32", "negative": "#C62828", "neutral": "#1565C0", "mixed": "#E65100"}.get(s, "#555")

def _sentiment_badge(s: str) -> str:
    icons = {"positive": "✅", "negative": "⚠️", "neutral": "ℹ️", "mixed": "⚡"}
    return icons.get(s, "•")

def _display_prediction_card(item: dict, show_rule: bool = True):
    """Render a single prediction card with color coding."""
    sentiment = item.get("sentiment", "neutral")
    color = _sentiment_color(sentiment)
    badge = _sentiment_badge(sentiment)
    rule  = item.get("rule", "")
    text  = item.get("text", item.get("effect", ""))
    src   = item.get("source", "")
    rule_html = f"<small style='color:#888'>{rule}</small><br>" if show_rule and rule else ""
    st.markdown(f"""<div style='border-left:4px solid {color};padding:8px 12px;
        margin:5px 0;background:{color}11;border-radius:4px'>
        {rule_html}{badge} {text} <small style='color:#aaa'>{src}</small>
    </div>""", unsafe_allow_html=True)

def _display_predictions_tab(chart: dict):
    """Full predictions page from book-sourced knowledge + DB."""
    name = chart.get("_name", "Native")
    st.markdown(f"### 🔮 Predictions for **{name}**")

    # Calculate special lagnas
    with st.spinner("Computing special lagnas, chara karakas, argalas..."):
        try:
            sl = calculate_special_lagnas(
                chart, chart["_birth_date"], chart["_birth_time"],
                chart["lat"], chart["lon"], chart.get("_tz", "Asia/Kolkata")
            )
        except Exception as e:
            st.warning(f"Special lagna calc note: {e}")
            sl = {"hora_lagna": {}, "ghati_lagna": {}, "sree_lagna": {},
                  "arudha_lagna": {}, "upapada_lagna": {}, "chara_karakas": {}}

        predictions = generate_predictions(chart, sl)
        summary     = generate_summary(chart, predictions, sl)

    # ── SUMMARY ──
    st.markdown("#### 📋 Chart Summary")
    st.markdown(summary)

    # ── SPECIAL LAGNAS ──
    st.markdown("---")
    st.markdown("#### 🌟 Special Lagnas")
    lagna_cols = st.columns(5)
    lagna_info = [
        ("Hora\n(Wealth)", sl.get("hora_lagna", {})),
        ("Ghati\n(Power)", sl.get("ghati_lagna", {})),
        ("Sree\n(Lakshmi)", sl.get("sree_lagna", {})),
        ("Arudha\n(Maya/Status)", sl.get("arudha_lagna", {})),
        ("Upapada\n(Spouse)", sl.get("upapada_lagna", {})),
    ]
    for col, (label, info) in zip(lagna_cols, lagna_info):
        with col:
            st.markdown(f"""<div style='text-align:center;padding:10px;
                background:#FFF8E1;border-radius:8px;border:1px solid #DAA520'>
                <div style='font-size:0.75rem;color:#888'>{label}</div>
                <div style='font-size:1.1rem;font-weight:700;color:#B8860B'>
                {info.get("sign_name","—")}</div>
            </div>""", unsafe_allow_html=True)

    # ── CHARA KARAKAS ──
    st.markdown("---")
    st.markdown("#### 👑 Chara Karakas (Variable Significators)")
    ck = sl.get("chara_karakas", {})
    if ck:
        ck_cols = st.columns(4)
        ck_items = list(ck.items())
        karaka_desc = {
            "AtmaKaraka": "Soul / Self",
            "AmatyaKaraka": "Career / Minister",
            "BhatriKaraka": "Siblings",
            "MatriKaraka": "Mother",
            "PitriKaraka": "Father",
            "PutraKaraka": "Children",
            "GnaatiKaraka": "Rivals",
            "DaraKaraka": "Spouse",
        }
        for i, (karaka, planet) in enumerate(ck_items):
            with ck_cols[i % 4]:
                st.markdown(f"""<div style='padding:8px;background:#E8F5E9;
                    border-radius:6px;margin:3px;text-align:center'>
                    <div style='font-size:0.7rem;color:#555'>{karaka}</div>
                    <div style='font-size:0.65rem;color:#888'>{karaka_desc.get(karaka,"")}</div>
                    <div style='font-size:1rem;font-weight:700;color:#1B5E20'>{planet}</div>
                </div>""", unsafe_allow_html=True)

    # ── ACTIVE YOGAS ──
    if predictions.get("yogas_active"):
        st.markdown("---")
        st.markdown("#### ✨ Active Yogas & Combinations")
        for yoga in predictions["yogas_active"]:
            type_colors = {"raja": "#DAA520", "dhana": "#2E7D32", "spiritual": "#6A1B9A",
                          "arishta": "#C62828", "health": "#E65100", "general": "#1565C0"}
            tc = type_colors.get(yoga.get("type",""), "#555")
            st.markdown(f"""<div style='border-left:4px solid {tc};padding:10px 14px;
                margin:6px 0;background:{tc}11;border-radius:4px'>
                <b>{yoga['name']}</b>
                <span style='background:{tc};color:white;padding:2px 6px;
                border-radius:10px;font-size:0.7rem;margin-left:8px'>{yoga.get('type','').upper()}</span><br>
                {yoga['effect']}<br>
                <small style='color:#aaa'>{yoga.get('source','')} | Strength: {yoga.get('strength','')}</small>
            </div>""", unsafe_allow_html=True)

    # ── NEECHA BHANGA ──
    if predictions.get("neecha_bhanga"):
        st.markdown("---")
        st.markdown("#### ⚡ Neecha Bhanga (Cancellation of Debilitation)")
        for nb in predictions["neecha_bhanga"]:
            st.markdown(f"""<div style='border-left:4px solid #F57F17;padding:10px 14px;
                margin:6px 0;background:#FFF8E111;border-radius:4px'>
                <b>{nb['planet']}</b> debilitated in <b>{nb['sign']}</b> — {nb['cancellation']}
                <small style='color:#aaa'> {nb['source']}</small>
            </div>""", unsafe_allow_html=True)

    # ── MAIN PREDICTION DOMAINS ──
    st.markdown("---")
    domain_tabs = st.tabs(["💰 Wealth", "💼 Career", "💑 Marriage", "🏥 Health",
                            "⏳ Timing", "🙏 Spiritual", "🔗 Argala", "🌐 Special Lagnas"])

    domain_data = [
        (predictions.get("wealth", []),    "wealth"),
        (predictions.get("career", []),    "career"),
        (predictions.get("marriage", []),  "marriage"),
        (predictions.get("health", []) + predictions.get("disease_watch",[]), "health"),
        (predictions.get("timing", []),    "timing"),
        (predictions.get("spiritual", []), "spiritual"),
        (predictions.get("argala_reading", []), "argala"),
        (predictions.get("special_lagnas_reading", []), "special"),
    ]

    for tab, (items, domain) in zip(domain_tabs, domain_data):
        with tab:
            if not items:
                st.info("No specific predictions found for this domain based on chart configuration.")
                continue
            if domain == "timing":
                for item in items:
                    st.markdown(f"**{item.get('dasha','')}**")
                    cols = st.columns(2)
                    with cols[0]:
                        st.markdown(f"**General:** {item.get('general','')}")
                        st.markdown(f"**Wealth:** {item.get('wealth','')}")
                        st.markdown(f"**Health:** {item.get('health','')}")
                    with cols[1]:
                        st.markdown(f"**Relationships:** {item.get('relationship','')}")
                        st.markdown(f"**Career:** {item.get('career','')}")
                    st.caption(item.get('source',''))
            elif domain == "health":
                for item in items:
                    if "body_part" in item:  # disease_watch entry
                        st.markdown(f"""<div style='border-left:4px solid #E65100;padding:8px 12px;
                            margin:5px 0;background:#FBE9E711;border-radius:4px'>
                            ⚕️ <b>{item['body_part']}</b> ({item.get('organ','')}) — {item['effect']}<br>
                            <small>💊 Remedy: {item.get('remedy','')}</small>
                            <small style='color:#aaa'> {item.get('source','')}</small>
                        </div>""", unsafe_allow_html=True)
                    else:
                        _display_prediction_card(item)
            elif domain == "argala":
                for item in items:
                    planets_str = ", ".join(item.get("planets", []))
                    st.markdown(f"""<div style='border-left:4px solid #1565C0;padding:8px 12px;
                        margin:5px 0;background:#E3F2FD11;border-radius:4px'>
                        🔗 <b>{item.get('position','')}</b> | Planets: <b>{planets_str}</b>
                        ({item.get('nature','')})<br>{item.get('text','')}
                        <small style='color:#aaa'> {item.get('source','')}</small>
                    </div>""", unsafe_allow_html=True)
            elif domain == "special":
                for item in items:
                    st.markdown(f"""<div style='border-left:4px solid #6A1B9A;padding:8px 12px;
                        margin:5px 0;background:#F3E5F511;border-radius:4px'>
                        🌟 <b>{item.get('lagna','')}</b> in <b>{item.get('sign','')}</b><br>
                        {item.get('text','')}
                        <small style='color:#aaa'> {item.get('source','')}</small>
                    </div>""", unsafe_allow_html=True)
            else:
                for item in items:
                    _display_prediction_card(item)

    # ── CHARA KARAKA READINGS ──
    if predictions.get("chara_karaka_reading"):
        st.markdown("---")
        st.markdown("#### 👑 Chara Karaka Detailed Readings")
        for item in predictions["chara_karaka_reading"]:
            st.markdown(f"""<div style='border-left:4px solid #2E7D32;padding:8px 12px;
                margin:4px 0;background:#E8F5E911;border-radius:4px'>
                <b>{item['karaka']}</b> = <b>{item['planet']}</b> — {item['text']}
                <small style='color:#aaa'> {item.get('source','')}</small>
            </div>""", unsafe_allow_html=True)

    # ── GENERAL PREDICTIONS ──
    if predictions.get("general"):
        st.markdown("---")
        st.markdown("#### 🌍 General Life Predictions")
        for item in predictions["general"]:
            _display_prediction_card(item)


def _display_full_chart(chart: dict, dark_mode: bool = False):
    name = chart.get("_name", "Native")
    st.markdown(f"## Chart of **{name}**")
    st.caption(f"Born: {chart.get('_birth_date')} at {chart.get('_birth_time')} · {chart.get('_birth_place')}")
    st.caption(f"Lagna: **{chart['lagna_sign_name']}** {chart['lagna_degree']:.2f}° | Ayanamsha (Lahiri): {chart['ayanamsha']:.2f}°")

    col_chart, col_table = st.columns([1, 1.2])
    with col_chart:
        fig = render_south_indian_chart(chart, title=f"{name}", dark_mode=dark_mode)
        st.plotly_chart(fig, use_container_width=True)
    with col_table:
        st.markdown('<div class="section-title">Planetary Positions</div>', unsafe_allow_html=True)
        df = pd.DataFrame(render_planet_table(chart))
        st.dataframe(df, hide_index=True, use_container_width=True)

    # Dasha
    st.markdown('<div class="section-title">⏳ Current Dasha Period</div>', unsafe_allow_html=True)
    _display_dasha(chart["dasha"])

    # Yogas
    if chart["yogas"]:
        st.markdown('<div class="section-title">✨ Special Yogas Detected</div>', unsafe_allow_html=True)
        for yoga in chart["yogas"]:
            st.markdown(f"""<div class="yoga-card">
                <b>{yoga['name']}</b> — {yoga['description']}<br>
                <small>Planets involved: {', '.join(yoga['planets'])}</small>
            </div>""", unsafe_allow_html=True)

    # Conjunctions
    if chart["conjunctions"]:
        st.markdown('<div class="section-title">🌀 Conjunctions</div>', unsafe_allow_html=True)
        for conj in chart["conjunctions"]:
            p_str = " + ".join(conj["planets"])
            pos   = ", ".join(conj["positive"]) or "—"
            ch    = ", ".join(conj["challenges"]) or "—"
            st.markdown(f"""<div class="conjunction-card">
                <b>{conj['name']}</b> — House {conj['house']} ({p_str})<br>
                {conj['behavior']}<br>
                ✅ <b>Positive:</b> {pos}<br>
                ⚠️ <b>Challenges:</b> {ch}
            </div>""", unsafe_allow_html=True)

    # Planet-in-house interpreter
    st.markdown('<div class="section-title">🪐 Planet-in-House Interpreter</div>', unsafe_allow_html=True)
    planet_order  = ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn","Rahu","Ketu"]
    sel_planet    = st.selectbox("Select planet:", planet_order, key="planet_select_single")
    if sel_planet:
        pdata  = chart["planets"][sel_planet]
        key    = (sel_planet, pdata["house"])
        interp = PLANET_IN_HOUSE.get(key, {})
        if interp:
            retro = " ⟲ Retrograde" if pdata.get("retrograde") else ""
            st.markdown(f"""<div class="planet-card">
                <h4>{interp['title']}</h4>
                <b>Sign:</b> {pdata['sign_name']} &nbsp;|&nbsp;
                <b>House:</b> {pdata['house']} &nbsp;|&nbsp;
                <b>Nakshatra:</b> {pdata['nakshatra_name']} Pada {pdata['pada']} &nbsp;|&nbsp;
                <b>Degree:</b> {pdata['degree']:.2f}°{retro}
            </div>""", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**🧠 Behavior & Personality**")
                st.write(interp.get("behavior",""))
                st.markdown("**✅ Positive Traits**")
                for p in interp.get("positive", []):
                    st.markdown(f"- {p}")
            with c2:
                st.markdown("**⚠️ Challenges**")
                for ch in interp.get("challenges", []):
                    st.markdown(f"- {ch}")
                st.markdown("**💼 Career**")
                st.write(interp.get("career",""))
            st.markdown("**❤️ Relationships**")
            st.write(interp.get("relationships",""))
            st.markdown("**🙏 Spiritual**")
            st.write(interp.get("spiritual",""))

    # Aspects
    with st.expander("🔗 Planetary Aspects (Drishti)"):
        for asp in chart["aspects"]:
            aspected = ", ".join(asp["aspected_planets"]) if asp["aspected_planets"] else "no planets"
            st.markdown(f"**{asp['from_planet']}** (H{asp['from_house']}) "
                        f"→ House {asp['aspected_house']} ({aspected})")

    # All houses
    with st.expander("🏠 All Houses — Planets & Significations"):
        for h in range(1, 13):
            hdata = HOUSES[h]
            here  = [p for p, d in chart["planets"].items() if d["house"] == h]
            planet_str = ", ".join(here) if here else "*Empty*"
            st.markdown(f"**H{h} — {hdata['name']}** | {planet_str}")
            st.caption(f"{', '.join(hdata['significations'])}")


def _display_comparison(c1: dict, c2: dict):
    st.markdown("---")
    st.markdown("## ⚖️ Chart Comparison")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"### {c1.get('_name','Person 1')}")
        st.plotly_chart(render_south_indian_chart(c1, title=c1.get("_name","P1")), use_container_width=True)
        st.caption(f"Lagna: {c1['lagna_sign_name']} | Moon: {c1['planets']['Moon']['sign_name']}")
    with col2:
        st.markdown(f"### {c2.get('_name','Person 2')}")
        st.plotly_chart(render_south_indian_chart(c2, title=c2.get("_name","P2")), use_container_width=True)
        st.caption(f"Lagna: {c2['lagna_sign_name']} | Moon: {c2['planets']['Moon']['sign_name']}")

    compat = compare_charts(c1, c2)
    st.markdown("### 💑 Compatibility Analysis")
    score_col, detail_col = st.columns([1, 2])
    with score_col:
        score = compat["overall_score"]
        label = compat["overall_label"]
        color = ("#4CAF50" if score >= 70 else "#FF9800" if score >= 45 else "#F44336")
        st.markdown(f"""<div style='text-align:center;padding:20px;border-radius:12px;
            background:{color}20;border:2px solid {color};'>
            <div style='font-size:3rem;font-weight:800;color:{color};'>{score}%</div>
            <div style='font-size:1.2rem;color:{color};'>{label}</div>
        </div>""", unsafe_allow_html=True)
    with detail_col:
        mc = compat["moon_compatibility"]
        lc = compat["lagna_compatibility"]
        st.markdown(f"""
| Factor | {c1.get('_name','P1')} | {c2.get('_name','P2')} | Rating |
|--------|---------|---------|--------|
| Moon Sign | {mc['person1_moon']} | {mc['person2_moon']} | **{mc['rating']}** |
| Lagna | {lc['person1_lagna']} | {lc['person2_lagna']} | **{lc['rating']}** |
""")
        st.write(mc["description"])

    st.markdown("**❤️ Venus-Mars Attraction**")
    for note in compat["venus_mars_attraction"]:
        st.markdown(f"- {note}")

    if compat["shared_energies"]:
        st.markdown("**🔗 Shared Sign Energies**")
        for se in compat["shared_energies"]:
            st.markdown(f"- {c1.get('_name','P1')}'s **{se['chart1_planet']}** + "
                        f"{c2.get('_name','P2')}'s **{', '.join(se['chart2_planets'])}** "
                        f"in **{se['sign']}** — {se['note']}")

    with st.expander("🔭 Side-by-side Planet Positions"):
        r1 = pd.DataFrame(render_planet_table(c1)).set_index("Planet")
        r2 = pd.DataFrame(render_planet_table(c2)).set_index("Planet")
        combined = r1.join(r2, lsuffix=f" ({c1.get('_name','P1')})",
                           rsuffix=f" ({c2.get('_name','P2')})")
        st.dataframe(combined, use_container_width=True)


def _display_reference():
    st.markdown("## 📚 Vedic Astrology Reference")
    ref_tab = st.radio("Section:", [
        "Planets", "Signs", "Houses", "Nakshatras", "Yogas", "Planet-in-House Quick Ref"
    ], horizontal=True)

    if ref_tab == "Planets":
        for name, info in PLANETS_INFO.items():
            with st.expander(f"{info['symbol']} **{name}** ({info['sanskrit']})"):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**Nature:** {info['nature']} | **Gender:** {info['gender']}")
                    st.markdown(f"**Karaka:** {', '.join(info['karaka'])}")
                    st.markdown(f"**Gem:** {info['gem']} | **Day:** {info['day']}")
                    st.markdown(f"**Friends:** {', '.join(info['friends'])}")
                    st.markdown(f"**Enemies:** {', '.join(info['enemies'])}")
                with c2:
                    own   = [SIGNS[s]["name"] for s in info.get("own_sign", [])]
                    exalt = SIGNS[info["exaltation"]]["name"] + f" at {info['exalt_degree']}°"
                    debil = SIGNS[info["debilitation"]]["name"] + f" at {info['debil_degree']}°"
                    st.markdown(f"**Own:** {', '.join(own)}")
                    st.markdown(f"**Exaltation:** {exalt}")
                    st.markdown(f"**Debilitation:** {debil}")
                    st.markdown(f"**Body Parts:** {', '.join(info['body_parts'])}")
                st.write(info["description"])

    elif ref_tab == "Signs":
        rows = [{"Sign": s["name"], "Sanskrit": s["sanskrit"], "Lord": s["lord"],
                 "Element": s["element"], "Quality": s["quality"], "Gender": s["gender"]}
                for s in SIGNS.values()]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    elif ref_tab == "Houses":
        for num, h in HOUSES.items():
            with st.expander(f"**House {num} — {h['name']}** ({h['type']})"):
                st.markdown(f"**Sanskrit:** {h['sanskrit']} | **Body:** {h['body_part']} | **Goal:** {h['dharma_artha']}")
                st.markdown(f"**Significations:** {', '.join(h['significations'])}")

    elif ref_tab == "Nakshatras":
        rows = [{"#": i+1, "Name": n["name"], "Lord": n["lord"], "Deity": n["deity"],
                 "Symbol": n["symbol"], "Degrees": n["degrees"]}
                for i, n in NAKSHATRAS.items()]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        sel = st.selectbox("Details:", [f"{i+1}. {n['name']}" for i, n in NAKSHATRAS.items()])
        if sel:
            idx = int(sel.split(".")[0]) - 1
            n   = NAKSHATRAS[idx]
            st.markdown(f"**{n['name']}** | Lord: **{n['lord']}** | Deity: {n['deity']} | Guna: {n['guna']}")
            st.write(n["description"])

    elif ref_tab == "Yogas":
        for yoga in RAJ_YOGAS:
            with st.expander(f"**{yoga['name']}**"):
                st.markdown(f"**Condition:** {yoga['condition']}")
                st.write(yoga["description"])
                st.markdown(f"**Effects:** {', '.join(yoga['effects'])}")
                if "sub_yogas" in yoga:
                    for sub, sub_data in yoga["sub_yogas"].items():
                        st.markdown(f"- **{sub} ({sub_data['planet']}):** {sub_data['effect']}")

    elif ref_tab == "Planet-in-House Quick Ref":
        planet_sel = st.selectbox("Planet:", list(PLANETS_INFO.keys()))
        house_sel  = st.selectbox("House:", list(range(1, 13)))
        interp = PLANET_IN_HOUSE.get((planet_sel, house_sel))
        if interp:
            st.markdown(f"### {interp['title']}")
            st.write(interp["behavior"])
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Positive**")
                for p in interp["positive"]:
                    st.markdown(f"- {p}")
            with c2:
                st.markdown("**Challenges**")
                for ch in interp["challenges"]:
                    st.markdown(f"- {ch}")
            st.markdown(f"**Career:** {interp['career']}")
            st.markdown(f"**Health:** {interp['health']}")
            st.markdown(f"**Relationships:** {interp['relationships']}")
            st.markdown(f"**Spiritual:** {interp['spiritual']}")


# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown('<div class="main-header">🪐 South Vedic Astrology Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">South Indian Chart · Planets · Conjunctions · Yogas · Compatibility</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["🔭 Single Chart Analysis", "🔮 Predictions", "🔀 Chart Comparison", "📚 Vedic Reference"])

# ── TAB 1 ──────────────────────────────────
with tab1:
    st.markdown("### Enter Birth Details")
    with st.form("single_chart_form"):
        name, birth_date, birth_time_val, birth_place, tz_choice = birth_input_form("p1")
        dark_mode = st.checkbox("Dark chart theme", value=False)
        submitted = st.form_submit_button("✨ Calculate Chart", use_container_width=True)

    if submitted:
        chart = do_calculate(name, birth_date, birth_time_val, birth_place, tz_choice)
        if chart:
            st.session_state["chart1"] = chart
            st.session_state["dark1"]  = dark_mode

    if st.session_state.get("chart1"):
        _display_full_chart(st.session_state["chart1"],
                            dark_mode=st.session_state.get("dark1", False))

# ── TAB 2 — PREDICTIONS ──────────────────────
with tab2:
    chart_for_pred = st.session_state.get("chart1")
    if chart_for_pred:
        _display_predictions_tab(chart_for_pred)
    else:
        st.info("👈 First calculate a chart in the **Single Chart Analysis** tab, then come back here for full predictions.")
        st.markdown("""
**What's included in Predictions:**
- 🌟 Special Lagnas — Hora (Wealth), Ghati (Power), Sree (Lakshmi), Arudha (Status), Upapada (Spouse)
- 👑 Chara Karakas — AtmaKaraka (Soul), DaraKaraka (Spouse), AmatyaKaraka (Career), and all 8
- ✨ Active Yogas — Raja, Dhana, Spiritual, and Arishta yogas with effects
- ⚡ Neecha Bhanga — Debilitation cancellation analysis
- 💰 Wealth — 2nd/11th lord analysis, Jupiter strength, Kerala prosperity rules
- 💼 Career — 10th lord, Ghati Lagna, Sun placement, career yogas
- 💑 Marriage — Venus, 7th lord, Upapada Lagna, spouse quality
- 🏥 Health — Disease indicators, organ-specific risks, remedies
- ⏳ Dasha Timing — Current Mahadasha/Antardasha effects across all life areas
- 🙏 Spiritual — Moksha yoga, 12th house, Ketu placement, dharmic path
- 🔗 Argala — Intervention analysis on Lagna from 2nd, 4th, 11th houses

*All predictions sourced from Kerala Jyotisha [K] and Vedic Astrology Integrated Approach [VI]*
""")

# ── TAB 3 ──────────────────────────────────
with tab3:
    st.markdown("### Person 1")
    with st.form("person1_form"):
        n1, d1, t1, p1, tz1 = birth_input_form("c1")
        s1 = st.form_submit_button("Calculate Person 1", use_container_width=True)
    if s1:
        c1 = do_calculate(n1, d1, t1, p1, tz1)
        if c1:
            st.session_state["comp_chart1"] = c1

    st.markdown("### Person 2")
    with st.form("person2_form"):
        n2, d2, t2, p2, tz2 = birth_input_form("c2")
        s2 = st.form_submit_button("Calculate Person 2", use_container_width=True)
    if s2:
        c2 = do_calculate(n2, d2, t2, p2, tz2)
        if c2:
            st.session_state["comp_chart2"] = c2

    cc1 = st.session_state.get("comp_chart1")
    cc2 = st.session_state.get("comp_chart2")
    if cc1 and cc2:
        if st.button("🔀 Compare Charts", use_container_width=True):
            _display_comparison(cc1, cc2)
        elif "comp_result" in st.session_state:
            _display_comparison(cc1, cc2)
    elif cc1:
        st.info("Person 1 calculated ✓ — now enter Person 2 details.")
    elif cc2:
        st.info("Person 2 calculated ✓ — now enter Person 1 details.")

# ── TAB 4 ──────────────────────────────────
with tab4:
    _display_reference()
