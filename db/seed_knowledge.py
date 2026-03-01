"""
seed_knowledge.py — Build and populate the Vedic Astrology SQLite knowledge base.
Sources:
  [K]  = Kerala Jyotisha (Sage Sukracharya / OP Verma)
  [VI] = Vedic Astrology Integrated Approach (P.V.R. Narasimha Rao)
  [VM] = Varahamihira Hora Sastram
  [P]  = Parasara Hora Sastra (classical)
Run:  python3 db/seed_knowledge.py
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), "vedic_knowledge.db")

# ─────────────────────────────────────────────────────────────────────────────
# SCHEMA
# ─────────────────────────────────────────────────────────────────────────────
SCHEMA = """
CREATE TABLE IF NOT EXISTS lagna_lord_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lagna_lord_house   INTEGER,   -- house where lagna lord is placed (1-12)
    condition          TEXT,      -- extra condition (strength, aspect, sign etc.)
    effect             TEXT NOT NULL,
    category           TEXT,      -- wealth|health|career|relationship|character|general
    sentiment          TEXT,      -- positive|negative|neutral|mixed
    source             TEXT
);

CREATE TABLE IF NOT EXISTS house_lord_in_house (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lord_of_house      INTEGER NOT NULL,
    placed_in_house    INTEGER NOT NULL,
    effect             TEXT NOT NULL,
    category           TEXT,
    sentiment          TEXT,
    source             TEXT
);

CREATE TABLE IF NOT EXISTS yogas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name               TEXT NOT NULL,
    yoga_type          TEXT,      -- raja|dhana|health|spiritual|negative|arishta
    condition_rule     TEXT NOT NULL,
    planets_involved   TEXT,
    effect             TEXT NOT NULL,
    strength           TEXT,      -- strong|moderate|weak
    source             TEXT
);

CREATE TABLE IF NOT EXISTS special_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_type          TEXT NOT NULL,  -- prosperity|poverty|disease|longevity|marriage|career|character|foreign
    condition          TEXT NOT NULL,
    effect             TEXT NOT NULL,
    sentiment          TEXT,
    source             TEXT
);

CREATE TABLE IF NOT EXISTS disease_yogas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    body_part          TEXT,
    organ_system       TEXT,
    condition          TEXT NOT NULL,
    planets_involved   TEXT,
    houses_involved    TEXT,
    effect             TEXT NOT NULL,
    remedy             TEXT,
    source             TEXT
);

CREATE TABLE IF NOT EXISTS dasha_effects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dasha_planet       TEXT NOT NULL,
    placement_house    INTEGER,
    sign_nature        TEXT,      -- own|exalt|debil|friend|enemy|neutral
    general_effects    TEXT NOT NULL,
    wealth_effects     TEXT,
    health_effects     TEXT,
    relationship_effects TEXT,
    career_effects     TEXT,
    source             TEXT
);

CREATE TABLE IF NOT EXISTS special_lagna_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lagna_type         TEXT NOT NULL,  -- Hora|Ghati|Sree|Arudha|Upapada|Karakamsa
    aspect_house       INTEGER,        -- house from that lagna (1=lagna itself, 7=7th from it, etc.)
    planet             TEXT,
    condition          TEXT,
    effect             TEXT NOT NULL,
    category           TEXT,
    source             TEXT
);

CREATE TABLE IF NOT EXISTS chara_karaka_effects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    karaka             TEXT NOT NULL,  -- AtmaKaraka|AmatyaKaraka|BhatriKaraka|etc.
    karaka_planet      TEXT,           -- planet acting as this karaka (null = general rule)
    house_in_rasi      INTEGER,        -- house of karaka in rasi chart
    sign               TEXT,           -- sign of karaka
    effect             TEXT NOT NULL,
    category           TEXT,
    source             TEXT
);

CREATE TABLE IF NOT EXISTS argala_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    argala_type        TEXT NOT NULL,  -- Primary|Secondary|Virodha
    from_position      INTEGER,        -- position from reference (2,4,5,11)
    planet_nature      TEXT,           -- benefic|malefic|any
    effect_on_reference TEXT NOT NULL,
    example            TEXT,
    source             TEXT
);

CREATE TABLE IF NOT EXISTS neecha_bhanga_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    condition          TEXT NOT NULL,  -- what cancels debilitation
    effect             TEXT NOT NULL,
    yoga_name          TEXT,
    source             TEXT
);

CREATE TABLE IF NOT EXISTS transit_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    planet             TEXT NOT NULL,
    transit_house      INTEGER,        -- house being transited (from natal moon)
    ashtakavarga_min   INTEGER,        -- minimum SAV rekhas for benefit
    effect             TEXT NOT NULL,
    timing_notes       TEXT,
    source             TEXT
);
"""

# ─────────────────────────────────────────────────────────────────────────────
# DATA
# ─────────────────────────────────────────────────────────────────────────────

LAGNA_LORD_RULES = [
    # ── LAGNA LORD IN 1ST ──
    (1, "strong, own/exalt sign", "Native is healthy, dignified, self-reliant, and rises by own merit. Long life and good constitution.", "character", "positive", "K"),
    (1, "weak or debilitated", "Native has a weak physique and faces early health issues. Lacks confidence.", "health", "negative", "K"),
    (1, "aspected by benefics", "Fortunate personality, respected, attractive appearance, kind nature.", "character", "positive", "K"),
    (1, "conjunct malefics", "Troubles to self, impulsive nature, accident-prone, ego conflicts.", "health", "negative", "K"),

    # ── LAGNA LORD IN 2ND ──
    (2, "strong", "Native becomes prosperous and wealthy after age 20. Good family, eloquent speech, financial focus.", "wealth", "positive", "K"),
    (2, "in enemy sign or weak", "Financial struggles, family conflicts, harsh speech. Delayed wealth.", "wealth", "negative", "K"),
    (2, "with 10th lord", "Wealth through profession and career. Earns well from early in life.", "wealth", "positive", "K"),

    # ── LAGNA LORD IN 3RD ──
    (3, "strong", "Courageous, good siblings, success in communication, writing, short journeys. Self-made through efforts.", "career", "positive", "K"),
    (3, "weak or malefic", "Sibling conflicts, cowardice, difficulties in communication ventures.", "relationship", "negative", "K"),
    (3, "with benefics", "Creative talent, artistic communication, supportive siblings.", "career", "positive", "VI"),

    # ── LAGNA LORD IN 4TH ──
    (4, "strong", "Happiness, good mother, property, vehicles, higher education. Settled and contented life.", "wealth", "positive", "K"),
    (4, "in own or exalt sign", "Land, property and real estate gains. Mother's support throughout life.", "wealth", "positive", "K"),
    (4, "with malefics", "Domestic troubles, mother's health issues, property disputes.", "health", "negative", "K"),

    # ── LAGNA LORD IN 5TH ──
    (5, "strong", "Intelligent, creative, blessed with good children. Speculative gains. Strong past-life merit (poorva punya).", "wealth", "positive", "K"),
    (5, "with Jupiter", "Highly intelligent, wise children, spiritual merit. May be a teacher or philosopher.", "character", "positive", "K"),
    (5, "with malefics", "Difficulties with children, speculative losses, ego in creativity.", "relationship", "negative", "K"),

    # ── LAGNA LORD IN 6TH ──
    (6, None, "Native faces sorrows, no comforts of life. Health issues, debts, enemies. Must work hard to succeed.", "health", "negative", "K"),
    (6, "with 6th lord", "Double dusthana — health very fragile, persistent enemies, financial struggles.", "health", "negative", "K"),
    (6, "strong planet in 6th", "Defeats enemies through sheer effort. Service-oriented career. Medical profession possible.", "career", "mixed", "K"),

    # ── LAGNA LORD IN 7TH ──
    (7, "strong", "Marriage is central to life. Good spouse, successful partnerships. May live in foreign land after marriage.", "relationship", "positive", "K"),
    (7, "with Venus", "Beautiful, charming spouse. Marriage brings happiness and wealth.", "relationship", "positive", "K"),
    (7, "with malefics or debilitated", "Marital conflicts, ego clashes in partnerships, possible separation.", "relationship", "negative", "K"),
    (7, "benefic aspect", "Public life brings respect. Business partnerships thrive.", "career", "positive", "VI"),

    # ── LAGNA LORD IN 8TH ──
    (8, None, "No comforts of life. Short life if heavily afflicted, or life marked by constant transformation and crises.", "health", "negative", "K"),
    (8, "strong", "Hidden strength, occult knowledge, gains through research or inheritance. Long-lived despite challenges.", "health", "mixed", "K"),
    (8, "with 8th lord", "Severe health issues, repeated setbacks, possible violent events or accidents.", "health", "negative", "K"),

    # ── LAGNA LORD IN 9TH ──
    (9, "strong", "Very fortunate. Father is a great support. High dharmic life, higher education, foreign travel for growth. Luck follows naturally.", "wealth", "positive", "K"),
    (9, "own/exalt sign", "Native becomes prosperous and wealthy throughout life. Good fortune is permanent.", "wealth", "positive", "K"),
    (9, "with Jupiter", "Philosopher, teacher, or spiritual guide. Exceptional luck and wisdom.", "character", "positive", "K"),

    # ── LAGNA LORD IN 10TH ──
    (10, "strong", "Excellent career and public reputation. High status, authority, government connections. Career is the primary expression of self.", "career", "positive", "K"),
    (10, "in own/exalt sign", "Native becomes prosperous and wealthy throughout life. Exceptional career rise.", "career", "positive", "K"),
    (10, "with 10th lord", "Rajayoga — native attains very high status, possibly fame in chosen field.", "career", "positive", "K"),
    (10, "with malefics", "Career conflicts, struggle for recognition, difficulties with authority.", "career", "negative", "K"),

    # ── LAGNA LORD IN 11TH ──
    (11, "strong", "Good income, fulfilled desires, large social network. Elder siblings are supportive. Gains come easily.", "wealth", "positive", "K"),
    (11, "with benefics", "Excellent financial gains, multiple income sources, respected in social circle.", "wealth", "positive", "K"),
    (11, "with malefics", "Income earned through struggle, conflicts in social circle, elder sibling challenges.", "wealth", "negative", "K"),

    # ── LAGNA LORD IN 12TH ──
    (12, None, "No comforts of life at birthplace. May settle in foreign land. Spiritual inclinations, hidden strength. Loss of vitality but gains in isolation.", "general", "negative", "K"),
    (12, "with benefics", "Foreign settlement brings success. Spiritual life is fulfilling. Bed pleasures and retreat bring renewal.", "general", "mixed", "K"),
    (12, "strong malefic", "Native passes whole life away from birthplace. Heavy losses, isolation, government persecution.", "general", "negative", "K"),
]

HOUSE_LORD_IN_HOUSE = [
    # 2nd lord placements
    (2, 1, "Wealth comes through personal effort and personality. Self-earned fortune. Financial focus on self.", "wealth", "positive", "VI"),
    (2, 2, "Excellent for accumulation. Wealth stays in family. Strong financial intelligence.", "wealth", "positive", "VI"),
    (2, 5, "Wealth through speculation, children, and creative work. Gains from investments.", "wealth", "positive", "VI"),
    (2, 9, "Wealth through higher education, religion, and father. Fortune from dharmic activities.", "wealth", "positive", "VI"),
    (2, 11, "Excellent income and financial gains. Multiple sources of wealth. Desires fulfilled through money.", "wealth", "positive", "VI"),
    (2, 6, "Financial struggles, debts. Money earned but spent on health or enemies.", "wealth", "negative", "VI"),
    (2, 8, "Sudden financial ups and downs. Inheritance possible but also sudden losses.", "wealth", "mixed", "VI"),
    (2, 12, "Heavy expenditure. Wealth goes to foreign lands or losses. Generosity depletes finances.", "wealth", "negative", "VI"),

    # 5th lord placements
    (5, 1, "Native is highly intelligent, creative, and self-expressive. Children reflect the native's personality.", "character", "positive", "K"),
    (5, 5, "Excellent for children, creativity, and intelligence. Strong past-life merit.", "wealth", "positive", "K"),
    (5, 9, "Extremely fortunate children. Creative wisdom in dharma. Philosophy and children are interlinked.", "relationship", "positive", "K"),
    (5, 11, "Children bring gains. Fulfilled creative desires. Speculation succeeds.", "wealth", "positive", "K"),
    (5, 6, "Difficulties with children. Creative efforts face opposition. Speculative losses.", "relationship", "negative", "K"),
    (5, 8, "Hidden talents. Occult creativity. Children face challenges or come through unusual circumstances.", "relationship", "mixed", "K"),
    (5, 12, "Children may be born abroad or live in foreign lands. Spiritual creativity. Creative isolation.", "relationship", "mixed", "K"),

    # 7th lord placements
    (7, 1, "Spouse reflects the native. Marriage is central to identity. Often early marriage.", "relationship", "positive", "K"),
    (7, 2, "Wealth through marriage. Spouse contributes to family finances. Family-oriented marriage.", "wealth", "positive", "K"),
    (7, 4, "Spouse brings domestic happiness. Home life is enriched by marriage. Mother approves of spouse.", "relationship", "positive", "K"),
    (7, 5, "Romantic marriage. Strong love before marriage. Intelligent and creative spouse.", "relationship", "positive", "K"),
    (7, 7, "Strong marriage focus. Spouse is independent. Business partnerships are central.", "relationship", "positive", "K"),
    (7, 9, "Spouse is foreign, from different culture, or highly educated. Marriage brings luck.", "relationship", "positive", "VI"),
    (7, 6, "Marriage conflicts. Spouse becomes adversarial. Legal trouble in marriage.", "relationship", "negative", "K"),
    (7, 8, "Transformation through marriage. Spouse's health issues. Intense, secretive relationship.", "relationship", "mixed", "K"),
    (7, 12, "Spouse may be foreign or from distant place. Hidden marriage. Bed pleasures important.", "relationship", "mixed", "K"),

    # 9th lord placements
    (9, 1, "Very fortunate personality. Luck is natural and follows the native. Father's blessings are strong.", "wealth", "positive", "K"),
    (9, 5, "Fortune through children and creativity. Philosophical intelligence. Teaching fortune.", "wealth", "positive", "K"),
    (9, 9, "Most fortunate placement. Exceptional luck, strong father, religious dharma is prominent.", "wealth", "positive", "K"),
    (9, 10, "Fortune through career. Dharmic profession. Government or teaching brings luck.", "career", "positive", "K"),
    (9, 11, "Luck manifests as income and gains. Desires fulfilled through fortune. Elder siblings are lucky.", "wealth", "positive", "K"),
    (9, 6, "Father may be adversarial or face health issues. Luck comes through service.", "general", "negative", "K"),
    (9, 8, "Father's health issues. Luck is hidden or comes through research and occult.", "general", "mixed", "K"),
    (9, 12, "Fortune in foreign lands. Spiritual luck. Father may live abroad.", "general", "mixed", "K"),

    # 10th lord placements
    (10, 1, "Career reflects personality. Self-made career. Leadership through personal charisma.", "career", "positive", "K"),
    (10, 5, "Creative career. Career in arts, education, or speculation. Children connected to career.", "career", "positive", "K"),
    (10, 9, "Dharmic career. Luck in profession. Foreign career connections. Teaching or religious profession.", "career", "positive", "K"),
    (10, 10, "Exceptional career. Self-contained professional power. Authority and government favor.", "career", "positive", "K"),
    (10, 11, "Career brings abundant gains. Income through profession is excellent.", "career", "positive", "K"),
    (10, 6, "Career in service, medicine, or law. Work challenges are common. Service-oriented profession.", "career", "mixed", "K"),
    (10, 8, "Hidden career or research profession. Career transformations. Occult or investigative work.", "career", "mixed", "K"),
    (10, 12, "Career in foreign land or isolated settings. Work in hospitals, research, or spiritual institutions.", "career", "mixed", "K"),

    # 11th lord placements
    (11, 1, "Income from self-effort. Gains through personality and personal initiative.", "wealth", "positive", "VI"),
    (11, 2, "Gains accumulate in family wealth. Family income is strong.", "wealth", "positive", "VI"),
    (11, 5, "Income from creative and speculative sources. Children contribute to gains.", "wealth", "positive", "VI"),
    (11, 10, "Career brings maximum gains. Professional income is the primary wealth source.", "wealth", "positive", "VI"),
    (11, 11, "Exceptional gains. Multiple income streams. Social network generates wealth.", "wealth", "positive", "VI"),
    (11, 6, "Income through service, healthcare, or legal work. Gains after effort and struggle.", "wealth", "mixed", "VI"),
    (11, 8, "Sudden and irregular gains. Inheritance. Hidden income sources.", "wealth", "mixed", "VI"),
    (11, 12, "Gains go to expenditure. Foreign income possible. Spending equals earning.", "wealth", "negative", "VI"),
]

YOGAS = [
    # ── RAJA YOGAS (from Kerala & Integrated) ──
    ("Neecha Bhanga Raja Yoga", "raja", "Debilitated planet's sign lord or exaltation sign lord is in kendra from lagna or Moon, or the debilitated planet is aspected by its exaltation lord", "Any debilitated planet", "Debilitation is cancelled. Native rises from humble origins to great heights. Especially powerful in 10th house.", "strong", "K"),
    ("Gaja Kesari Yoga", "raja", "Jupiter in kendra (1,4,7,10) from Moon", "Jupiter, Moon", "Fame, wisdom, wealth, and leadership. Respected like an elephant-lion. Benefic Jupiter aspect on Moon gives emotional wisdom and public support.", "strong", "VI"),
    ("Budhaditya Yoga", "raja", "Sun and Mercury conjunct in same house", "Sun, Mercury", "Sharp intelligence, eloquent speech, government recognition, and professional success in chosen field.", "strong", "VI"),
    ("Chandra-Mangal Yoga", "dhana", "Moon and Mars conjunct or in mutual aspect", "Moon, Mars", "Wealth through bold emotional intelligence. Business acumen, real estate gains, and financial drive.", "strong", "VI"),
    ("Pancha Mahapurusha - Ruchaka", "raja", "Mars in kendra in own sign (Aries/Scorpio) or exaltation (Capricorn)", "Mars", "Warrior greatness, athletic excellence, military leadership, and courage. Commands armies or organizations.", "strong", "VI"),
    ("Pancha Mahapurusha - Bhadra", "raja", "Mercury in kendra in own sign (Gemini/Virgo) or exaltation (Virgo)", "Mercury", "Intellectual greatness, communicative excellence, business mastery, and scholarship.", "strong", "VI"),
    ("Pancha Mahapurusha - Hamsa", "raja", "Jupiter in kendra in own sign (Sagittarius/Pisces) or exaltation (Cancer)", "Jupiter", "Spiritual greatness, noble character, wisdom, prosperity, and teaching excellence.", "strong", "VI"),
    ("Pancha Mahapurusha - Malavya", "raja", "Venus in kendra in own sign (Taurus/Libra) or exaltation (Pisces)", "Venus", "Luxurious life, artistic greatness, beauty, charm, and wealth in abundance.", "strong", "VI"),
    ("Pancha Mahapurusha - Shasha", "raja", "Saturn in kendra in own sign (Capricorn/Aquarius) or exaltation (Libra)", "Saturn", "Authority, long-lasting success, discipline, and service to society. Often becomes powerful administrator.", "strong", "VI"),
    ("Adhi Yoga", "raja", "Benefics (Mercury, Venus, Jupiter) in 6th, 7th, and 8th from Moon", "Mercury, Venus, Jupiter", "Native becomes a chief, minister, or leader. Comfortable, prosperous, healthy, and long-lived.", "strong", "VI"),
    ("Lakshmi Yoga", "dhana", "Lord of 9th in own/exalt sign in kendra, and Venus is strong", "9th lord, Venus", "Extreme wealth, beauty, and charm. Blessed by Goddess Lakshmi — prosperity throughout life.", "strong", "VI"),
    ("Saraswati Yoga", "raja", "Jupiter, Venus, and Mercury all in kendras, trikonas, or 2nd house", "Jupiter, Venus, Mercury", "Exceptional intelligence, artistic mastery, scholarly achievement, and teaching ability.", "strong", "VI"),
    ("Viparita Raja Yoga", "raja", "Lords of 6th, 8th, or 12th placed in each other's houses or in dusthana", "6th/8th/12th lords", "Rise to great heights through apparent adversity. Success from others' downfall. Hidden blessings.", "moderate", "VI"),

    # ── DHANA YOGAS (wealth) ──
    ("Dhana Yoga Type 1", "dhana", "Lords of 2nd and 11th conjunct in a strong house", "2nd lord, 11th lord", "Exceptional wealth accumulation. Double income-wealth axis creates financial prosperity.", "strong", "K"),
    ("Dhana Yoga Type 2", "dhana", "Lords of 5th and 9th conjunct or exchange", "5th lord, 9th lord", "Wealth from luck, speculation, children, and dharmic activities. Fortune multiplies over time.", "strong", "K"),
    ("Dhana Yoga Type 3", "dhana", "2nd lord in 9th or 9th lord in 2nd", "2nd lord, 9th lord", "Wealth through fortune and righteous living. Family finances linked to luck.", "moderate", "K"),
    ("Kubera Yoga", "dhana", "Jupiter in 2nd or 11th from lagna or Moon, strong", "Jupiter", "Immense wealth. Jupiter in income house brings divine financial grace.", "strong", "K"),

    # ── POVERTY / AFFLICTION YOGAS ──
    ("Daridra Yoga", "arishta", "Lord of lagna in 6th, 8th, or 12th, weak and afflicted", "Lagna lord", "Poverty, debts, and misfortune throughout life. Native struggles for basic comforts.", "strong", "K"),
    ("Kemadruma Yoga", "arishta", "No planets in 2nd or 12th from Moon, and Moon not conjunct or aspected by any planet", "Moon", "Loneliness, poverty, and lack of support. Mind is isolated. Misfortunes follow unless cancelled.", "strong", "K"),
    ("Shakat Yoga", "arishta", "Jupiter in 6th, 8th, or 12th from Moon", "Jupiter, Moon", "Reversal of fortune. Rising and falling repeatedly. Wealth not sustained.", "moderate", "K"),
    ("Grahan Yoga", "arishta", "Sun or Moon conjunct Rahu or Ketu", "Sun/Moon with Rahu/Ketu", "Eclipse-like life events. Mind is obsessive (Moon-Rahu) or ego-dissolving (Sun-Ketu). Disruptions in indicated areas.", "moderate", "VI"),

    # ── HEALTH YOGAS ──
    ("Sarpa Yoga", "health", "All planets within 180° (one half of zodiac)", "All planets", "Obstacles, bondage, and health issues. Life feels constrained. Lack of freedom.", "moderate", "K"),
    ("Vish Yoga", "health", "Moon conjunct Saturn in Taurus or Capricorn", "Moon, Saturn", "Emotional depression, chronic illness, mother's suffering. Mental health needs attention.", "strong", "K"),

    # ── SPIRITUAL YOGAS ──
    ("Pravrajya Yoga", "spiritual", "Four or more planets in one sign or house, especially with Saturn", "Multiple planets, Saturn", "Native may take to renunciation, spiritual life, or monkhood. Detachment from material world.", "moderate", "K"),
    ("Moksha Yoga", "spiritual", "Ketu or Jupiter in 12th, or 12th lord in 12th, strong lagna lord", "Ketu, Jupiter, 12th lord", "Liberation orientation. Native seeks moksha. Spiritual practices are central to life purpose.", "moderate", "VI"),
    ("Jnana Yoga", "spiritual", "Mercury, Jupiter, and Ketu forming trine or strong in 5th/9th", "Mercury, Jupiter, Ketu", "Native is a scholar of scriptures, philosopher, or spiritual teacher. Knowledge is the path.", "moderate", "VI"),
]

SPECIAL_RULES = [
    # ── PROSPERITY RULES (Kerala) ──
    ("prosperity", "Lagna lord is in extreme exaltation degrees in kendra/trikona, aspected by or conjunct 10th lord in own sign", "Native enjoys prosperity, fame, honor, wealth, and estates throughout life.", "positive", "K"),
    ("prosperity", "Strong lagna lord or navamsa lord in exaltation, kendra, or 11th house", "Native becomes prosperous and wealthy after age 30.", "positive", "K"),
    ("prosperity", "Lagna lord in own navamsa, exaltation navamsa, or vargottama, conjunct benefic", "Native enjoys prosperity and wealth throughout life, uninterrupted.", "positive", "K"),
    ("prosperity", "9th lord in own sign or exaltation in kendra", "Fortune and luck are permanent features of life. Lakshmi Yoga forms.", "positive", "K"),
    ("prosperity", "2nd lord and 10th lord exchange or conjunct", "Wealth through career is exceptional. Financial status rises with professional success.", "positive", "K"),

    # ── POVERTY RULES (Kerala) ──
    ("poverty", "Lagna lord in 6th, 8th, or 12th — no comforts of life", "Native faces persistent hardship, debts, and lack of comfort. Must work extremely hard.", "negative", "K"),
    ("poverty", "Lagna lord retrograde or hemmed between malefics (papakarti)", "Native suffers from incurable diseases and persistent misfortune.", "negative", "K"),
    ("poverty", "Lagna lord in enemy sign, debilitated, combust, conjunct malefics", "Native faces sorrows and difficulties. Character and health are weakened.", "negative", "K"),
    ("poverty", "No planet other than lagna lord is exalted — mediocre wealth only", "Native has mediocre wealth throughout life. Cannot achieve exceptional financial success.", "neutral", "K"),

    # ── FOREIGN TRAVEL / SETTLEMENT ──
    ("foreign", "Lagna lord in 12th or with strong malefic in debilitation sign in 12th", "Native passes whole life away from birthplace. Settles permanently in foreign country.", "mixed", "K"),
    ("foreign", "Lagna lord in friend's/own/exaltation sign aspected by planet in same state", "Native remains at native place throughout life. Strong roots.", "positive", "K"),
    ("foreign", "Rahu in 9th, 11th, or 12th, strong", "Foreign travel and connections are highlighted. Success through international exposure.", "positive", "VI"),

    # ── LONGEVITY RULES ──
    ("longevity", "8th lord from stronger of lagna or 7th in kendra", "Long life — native lives past normal lifespan.", "positive", "VI"),
    ("longevity", "8th lord from stronger of lagna or 7th in panaphara (2,5,8,11)", "Middle life — normal lifespan.", "neutral", "VI"),
    ("longevity", "8th lord from stronger of lagna or 7th in apoklima (3,6,9,12)", "Short life — life may be cut short unless strong protections exist.", "negative", "VI"),
    ("longevity", "Jupiter and Saturn both strong in chart", "Long, healthy life with wisdom in old age. Both dharma and karma planets are strong.", "positive", "K"),
    ("longevity", "Lagna lord hemmed between malefics AND 8th lord is weak", "Very short life, severe health issues throughout.", "negative", "K"),

    # ── MARRIAGE RULES ──
    ("marriage", "7th lord and Venus both strong, aspected by benefics", "Beautiful, loving, and long-lasting marriage. Spouse is charming and supportive.", "positive", "K"),
    ("marriage", "7th lord with Saturn or in Saturn's sign without benefic aspect", "Late marriage, serious or duty-based relationship. May marry an older person.", "mixed", "K"),
    ("marriage", "7th lord with Mars or with Rahu, no benefic aspect", "Marital conflicts, possible separation, or unconventional relationship.", "negative", "K"),
    ("marriage", "Venus in 7th strong, Jupiter aspecting 7th", "Ideal marriage conditions. Spouse is wise, beautiful, and loving.", "positive", "VI"),
    ("marriage", "Upapada Lagna lord strong and aspected by benefics", "Excellent conjugal happiness. Spouse is devoted and supportive.", "positive", "VI"),
    ("marriage", "Upapada Lagna lord in 6th, 8th, or 12th from UL", "Challenges in marriage. Possible separation or spouse health issues.", "negative", "VI"),

    # ── CAREER RULES ──
    ("career", "10th lord in kendra or trikona, strong", "Excellent career. Native rises to authority and public recognition.", "positive", "K"),
    ("career", "Saturn in 10th exalted or in own sign (Shasha Mahapurusha)", "Career longevity and authority. Success through discipline and hard work over time.", "positive", "VI"),
    ("career", "Sun in 10th", "Government career or leadership position. Public authority and recognition.", "positive", "K"),
    ("career", "10th lord with Rahu in strong position", "Unconventional career path. Success through technology, foreign companies, or innovation.", "mixed", "VI"),
    ("career", "Ghati Lagna strongly occupied by planets", "Fame, power, and authority in career. Native becomes a leader in their field.", "positive", "VI"),
    ("career", "Hora Lagna strongly occupied by Jupiter or Venus", "Financial success in career. Wealth through profession.", "positive", "VI"),

    # ── CHARACTER RULES ──
    ("character", "Lagna lord and Moon both strong, benefic aspect on lagna", "Virtuous, kind, and spiritually inclined character. Respected in society.", "positive", "K"),
    ("character", "Strong Sun and Jupiter in good houses", "Noble, righteous, and authoritative character. Natural leader with ethical foundation.", "positive", "K"),
    ("character", "Lagna lord with Mars and Saturn, no benefic", "Aggressive, harsh, and difficult character. Prone to conflicts.", "negative", "K"),
    ("character", "Mercury and Venus strong in lagna or 5th", "Charming, intelligent, and artistic character. Socially graceful.", "positive", "VI"),
]

DISEASE_YOGAS = [
    # ── EYE DISEASES (Kerala specific) ──
    ("Right eye", "Eyes", "Sun in 2nd afflicted by malefics OR 2nd lord weak with Rahu/Saturn", "Sun, Rahu, Saturn", "2", "Right eye problems, poor vision, or eye injury on right side.", "Sun propitiation, Ruby, Sun Namaskara", "K"),
    ("Left eye", "Eyes", "Moon in 2nd or 12th afflicted, or Moon with Rahu (eclipse)", "Moon, Rahu", "2, 12", "Left eye problems, vision issues, or emotional trauma affecting vision.", "Moon propitiation, Pearl, Chandra puja", "K"),
    ("Both eyes", "Eyes", "2nd and 12th lords both weak, Sun and Moon both afflicted", "Sun, Moon, malefics", "2, 12", "Severe eye diseases or blindness if heavily afflicted.", "Worship of Sun and Moon, Aditya Hridayam", "K"),
    ("Ear", "ENT", "3rd lord with malefics, or Saturn in 3rd afflicted, Mercury weak", "Saturn, Mercury", "3", "Hearing loss, ear infections, or deafness.", "Saturn propitiation, iron charity", "K"),
    ("Mouth/speech", "ENT", "2nd lord with malefics, Mercury afflicted in 2nd", "Mercury, malefics", "2", "Speech impediments, dental problems, or mouth diseases.", "Mercury propitiation, Green charity", "K"),

    # ── HEART DISEASES ──
    ("Heart", "Cardiovascular", "Sun afflicted in 4th or 5th, or Leo lagna with malefics in lagna", "Sun, Mars, Saturn", "4, 5", "Heart diseases, palpitations, or cardiac issues.", "Sun worship, Ruby, reduce stress", "K"),
    ("Blood pressure", "Cardiovascular", "Mars in lagna afflicted, or Sun with Rahu in fiery signs", "Mars, Sun, Rahu", "1, 5", "High blood pressure, blood disorders, inflammatory conditions.", "Mars propitiation, Coral, avoid anger", "K"),

    # ── MENTAL HEALTH ──
    ("Mind/Mental", "Nervous", "Moon afflicted by Saturn (Vish Yoga), or Moon with Rahu in lagna", "Moon, Saturn, Rahu", "1, 4", "Depression, anxiety, mental instability, or obsessive thoughts.", "Moon propitiation, Pearl, meditation", "K"),
    ("Nerves", "Nervous", "Mercury with Rahu or Saturn, or in 6th/8th heavily afflicted", "Mercury, Rahu, Saturn", "6, 8", "Nervous disorders, anxiety, skin diseases, speech problems.", "Mercury propitiation, Emerald", "VI"),

    # ── STOMACH / DIGESTION ──
    ("Stomach/Digestive", "Digestive", "Moon in 6th or afflicted in 4th, Jupiter with malefics in 5th", "Moon, Jupiter", "5, 6", "Digestive disorders, stomach ulcers, liver problems from over-indulgence.", "Moon worship, light diet, avoid dairy excess", "K"),
    ("Liver", "Digestive", "Jupiter with Saturn or in 6th heavily afflicted", "Jupiter, Saturn", "6", "Liver disorders, fatty liver, jaundice.", "Jupiter propitiation, Yellow Sapphire", "VI"),

    # ── JOINTS AND BONES ──
    ("Joints/Bones", "Musculoskeletal", "Saturn in lagna or aspecting lagna heavily, or Saturn with Mars", "Saturn, Mars", "1, 6", "Arthritis, joint pain, bone diseases, fractures.", "Saturn propitiation, Blue Sapphire, iron sesame charity", "K"),
    ("Skin", "Skin", "Mercury or Venus afflicted in 6th, or Rahu in lagna/6th", "Mercury, Venus, Rahu", "1, 6", "Skin diseases, rashes, allergies, or unusual skin conditions.", "Mercury puja, clean diet, avoid synthetic foods", "VI"),

    # ── REPRODUCTIVE / SEXUAL ──
    ("Reproductive", "Reproductive", "Venus or Mars heavily afflicted in 7th or 8th, or 7th lord with malefics", "Venus, Mars", "7, 8", "Reproductive health issues, sexual problems, or marital health challenges.", "Venus propitiation, Diamond, balanced lifestyle", "K"),
    ("Kidneys", "Urinary", "Venus in 6th or 8th afflicted, or 7th lord with Saturn", "Venus, Saturn", "6, 7, 8", "Kidney diseases, urinary tract issues, or water retention.", "Venus propitiation, clean water intake", "VI"),
]

DASHA_EFFECTS = [
    ("Sun", 1, "own", "Strong sense of self, leadership, government recognition, health is strong.", "Government contracts, salary rise, career in authority.", "Generally good, heart monitored.", "Ego in relationships, spouse may feel overshadowed.", "Leadership role, recognition, promotion.", "K"),
    ("Sun", 6, "enemy", "Conflicts with authority, health challenges especially eyes/heart, enemies rise.", "Financial strain from government disputes or taxes.", "Heart, eye problems likely.", "Father's health concerns, relationships suffer from ego.", "Career setbacks, conflicts with boss.", "K"),
    ("Sun", 10, "own", "Peak career period. Government recognition, promotions, public status rises.", "Income from authority and status positions.", "Good energy, watch for overwork.", "Spouse supports career ambitions.", "Best career period — authority and leadership.", "K"),
    ("Moon", 1, "own", "Emotional expansion, popularity with public, mother's blessings, mental wellbeing.", "Income from public/masses, domestic business.", "Good health, watch fluid retention.", "Nurturing relationships, motherly care received.", "Career in public-facing roles thrives.", "K"),
    ("Moon", 6, "enemy", "Mental anxiety, digestive issues, conflicts with women, mother's health concerns.", "Financial fluctuations, debts from health costs.", "Digestive, mental health issues.", "Emotional conflicts in relationships.", "Workplace stress, health-related work disruption.", "K"),
    ("Mars", 1, "own", "Courage, energy, initiative, physical strength peaks. Good for warriors and athletes.", "Earnings through courage, real estate, technical skills.", "Excellent physical energy, watch accidents.", "Passionate relationships, possible conflicts.", "Career advancement through bold action.", "K"),
    ("Mars", 8, "neutral", "Transformation period, accidents possible, occult interest, inheritance matters.", "Sudden gains or losses, inheritance-related activity.", "Surgery, accidents, blood pressure watch.", "Intense relationships, possible loss of loved one.", "Career upheaval, hidden opportunities.", "K"),
    ("Mercury", 1, "own", "Sharp intellect, communication thrives, business acumen, learning opportunities.", "Multiple income streams through communication and business.", "Good health, avoid over-thinking causing anxiety.", "Intellectual romantic connections, communication improves.", "Career in communication, business, or teaching flourishes.", "K"),
    ("Mercury", 6, "enemy", "Mental strain, communication problems, digestive issues, enemies through words.", "Financial disputes through contracts or communication.", "Nervous system, skin, digestive issues.", "Miscommunication in relationships.", "Work conflicts, contractual disputes.", "VI"),
    ("Jupiter", 1, "own", "Expansion, wisdom, financial growth, children's blessings, spiritual advancement.", "Significant wealth expansion, financial opportunities multiply.", "Excellent health, possible weight gain.", "Wise relationships, marriage prospects improve, children born.", "Career expansion, teaching, or spiritual leadership.", "K"),
    ("Jupiter", 6, "debil", "Wisdom misapplied, overconfidence with enemies, health from over-indulgence.", "Debts from generosity, financial excess.", "Liver, weight, over-eating issues.", "Relationship complications from over-idealism.", "Career expansion attempted but blocked.", "K"),
    ("Venus", 1, "own", "Love, beauty, luxury, relationships flourish. Arts and comforts peak.", "Wealth through beauty, arts, and luxury goods.", "Good health, reproductive health, skin glow.", "Marriage, romance, and relationships are peak.", "Career in arts, entertainment, luxury thrives.", "K"),
    ("Venus", 6, "debil", "Relationship conflicts, health from over-indulgence in pleasures.", "Spending on luxuries creates financial strain.", "Reproductive health, kidney issues.", "Love affairs with problems, workplace romance complications.", "Career in arts may face criticism.", "VI"),
    ("Saturn", 1, "own", "Discipline, hard work, slow but steady progress. Karma is being addressed.", "Steady income through persistent effort.", "Joint, bone health monitored. Longevity improves.", "Serious relationships, karmic meetings.", "Slow but solid career advancement. Government or law.", "K"),
    ("Saturn", 4, "neutral", "Domestic challenges, mother's health, property matters, emotional restriction.", "Property issues, home expenses rise.", "Chest, bones, emotional health.", "Home environment becomes serious or restrictive.", "Career growth blocked temporarily.", "K"),
    ("Saturn", 7, "neutral", "Karmic relationship year. Marriage tested. Late marriage if not yet done.", "Business partnerships tested, legal expenses.", "Kidneys, joint health.", "Marriage is most tested — communication and patience needed.", "Business partnerships restructured.", "K"),
    ("Rahu", 1, "exalt", "Obsessive drive for success, unconventional paths, foreign connections highlighted.", "Foreign income, technology-based earnings.", "Mysterious ailments, unusual health events.", "Unconventional relationships, foreign partner attraction.", "Technology, foreign career opportunities.", "VI"),
    ("Rahu", 9, "exalt", "Foreign travel, unconventional spiritual path, father complications.", "Income from foreign sources, international business.", "Long travel health considerations.", "Partner from different culture or background.", "International career growth.", "VI"),
    ("Ketu", 1, "exalt", "Spiritual awakening, detachment from ego, past-life patterns surface.", "Detachment from material gains, unexpected windfalls.", "Mysterious health issues, alternative medicine effective.", "Karmic relationships resolve, detachment from partner.", "Career confusion but hidden spiritual purpose.", "VI"),
    ("Ketu", 12, "exalt", "Liberation, moksha-orientation, foreign spiritual experiences, vivid dreams.", "Expenditure on spiritual causes, foreign income.", "Feet, sleep, immune system.", "Spiritual relationship or celibacy tendency.", "Career in foreign land or spiritual vocation.", "VI"),
]

SPECIAL_LAGNA_RULES = [
    # ── HORA LAGNA (wealth) ──
    ("Hora", 1, "Jupiter", "strong or own sign", "Exceptional wealth. Jupiter on Hora Lagna brings divine financial grace and expansion.", "wealth", "VI"),
    ("Hora", 1, "Venus", "strong or own sign", "Wealth through beauty, arts, and luxury. Venus on Hora Lagna brings comfortable prosperity.", "wealth", "VI"),
    ("Hora", 1, None, "benefics occupy or aspect", "Financial period is excellent. Money flows naturally.", "wealth", "VI"),
    ("Hora", 1, None, "malefics occupy without benefic aspect", "Financial challenges. Money earned with difficulty or lost.", "wealth", "VI"),
    ("Hora", 7, "Jupiter", "aspecting Hora Lagna", "Wealth through partnerships and marriage. Spouse contributes financially.", "wealth", "VI"),
    ("Hora", 11, None, "benefic occupying or aspecting", "Excellent income gains. The 11th from Hora Lagna shows income quality.", "wealth", "VI"),

    # ── GHATI LAGNA (power and fame) ──
    ("Ghati", 1, "Sun", "strong in or aspecting Ghati Lagna", "Supreme authority, government recognition, and political power.", "career", "VI"),
    ("Ghati", 1, "Mars", "strong in or aspecting Ghati Lagna", "Military or police authority. Leadership through courage.", "career", "VI"),
    ("Ghati", 1, None, "benefics occupy", "Fame and popularity in chosen field. Public recognition.", "career", "VI"),
    ("Ghati", 1, None, "Saturn occupies with no benefic", "Authority delayed but eventually comes through persistent discipline.", "career", "VI"),
    ("Ghati", 10, None, "strong planets", "Career fame and recognition in 10th from Ghati Lagna domain.", "career", "VI"),

    # ── SREE LAGNA (prosperity) ──
    ("Sree", 1, "Jupiter", "strong or own sign", "Lakshmi's grace — prosperity is uninterrupted. Jupiter on Sree Lagna is the best wealth indicator.", "wealth", "VI"),
    ("Sree", 1, "Venus", "exalted or own sign", "Beauty and wealth combined. Prosperous, comfortable, and aesthetically blessed life.", "wealth", "VI"),
    ("Sree", 1, None, "benefics aspect", "Prosperity flows naturally. Financial blessings throughout life.", "wealth", "VI"),
    ("Sree", 1, None, "malefics in Sree Lagna without benefic", "Prosperity is blocked. Wealth comes and goes. Financial instability.", "wealth", "VI"),
    ("Sree", 6, None, "malefics in 6th from Sree Lagna", "Enemies and debts diminish prosperity. Health expenses drain wealth.", "wealth", "VI"),
    ("Sree", 11, None, "benefics in 11th from Sree Lagna", "Excellent income and financial gains in Sudasa periods.", "wealth", "VI"),

    # ── ARUDHA LAGNA (reputation/perception) ──
    ("Arudha", 1, "Sun", "strong in or conjunct AL", "Native is perceived as a leader and authority figure in society.", "career", "VI"),
    ("Arudha", 1, "Venus", "strong in or conjunct AL", "Native is perceived as charming, beautiful, and socially graceful.", "character", "VI"),
    ("Arudha", 1, "Saturn", "in or conjunct AL", "Native is perceived as serious, reserved, or burdened. Public image is disciplined.", "character", "VI"),
    ("Arudha", 1, "Rahu", "in or conjunct AL", "Native is perceived as unconventional, mysterious, or controversial.", "character", "mixed"),
    ("Arudha", 7, None, "benefics in 7th from AL", "Business partnerships and public relationships are prosperous and harmonious.", "relationship", "VI"),
    ("Arudha", 11, None, "benefics in 11th from AL", "Financial gains are excellent. Public image generates income.", "wealth", "VI"),
    ("Arudha", 12, None, "malefics in 12th from AL", "Public image suffers losses. Reputation damage or financial fall from status.", "wealth", "VI"),

    # ── UPAPADA LAGNA (marriage/spouse) ──
    ("Upapada", 1, "Venus", "strong in or aspecting UL", "Beautiful, charming, and loving spouse. Marriage is a blessing.", "relationship", "VI"),
    ("Upapada", 1, "Jupiter", "aspecting UL strongly", "Wise, educated, and spiritual spouse. Marriage is a dharmic union.", "relationship", "VI"),
    ("Upapada", 1, "Saturn", "in or aspecting UL, no benefic", "Serious, older, or duty-based spouse. Marriage is delayed or restrictive.", "relationship", "VI"),
    ("Upapada", 1, "Mars", "in or conjunct UL without benefic", "Passionate but conflicted marriage. Manglik consideration for spouse.", "relationship", "VI"),
    ("Upapada", 7, None, "malefics in 7th from UL without benefic", "Separation, divorce, or spouse's early death in extreme cases.", "relationship", "VI"),
    ("Upapada", 2, "benefics", "in 2nd from UL", "Spouse brings wealth and family happiness. Marriage enriches life.", "relationship", "VI"),
]

CHARA_KARAKA_EFFECTS = [
    ("AtmaKaraka", None, 1, None, "Self is strongly expressed through personality. Native's soul purpose is evident to all. Lagna strength is enhanced.", "character", "VI"),
    ("AtmaKaraka", "Sun", None, None, "Soul purpose is authority, leadership, and dharma. Native is meant to lead and inspire.", "career", "VI"),
    ("AtmaKaraka", "Moon", None, None, "Soul purpose is nurturing, empathy, and public service. Emotional intelligence is the core gift.", "character", "VI"),
    ("AtmaKaraka", "Mars", None, None, "Soul purpose is courage, action, and righteousness. Native is a spiritual warrior.", "career", "VI"),
    ("AtmaKaraka", "Mercury", None, None, "Soul purpose is communication, intelligence, and teaching. Scholar or communicator of divine knowledge.", "career", "VI"),
    ("AtmaKaraka", "Jupiter", None, None, "Soul purpose is wisdom, dharma, and teaching. Natural guru energy — meant to guide others.", "character", "VI"),
    ("AtmaKaraka", "Venus", None, None, "Soul purpose is beauty, love, and divine art. Creative and romantic spiritual path.", "character", "VI"),
    ("AtmaKaraka", "Saturn", None, None, "Soul purpose is karma, discipline, and service. Life is a journey of karmic repayment and spiritual discipline.", "character", "VI"),
    ("AtmaKaraka", "Rahu", None, None, "Soul purpose is unconventional, worldly, and boundary-breaking. Past-life rebel or revolutionary soul.", "character", "VI"),
    ("AmatyaKaraka", "Jupiter", None, None, "Career in teaching, religion, law, or counseling. Wisdom is the professional gift.", "career", "VI"),
    ("AmatyaKaraka", "Mercury", None, None, "Career in communication, business, IT, or writing. Intelligence drives professional success.", "career", "VI"),
    ("AmatyaKaraka", "Venus", None, None, "Career in arts, beauty, entertainment, or diplomacy. Charm is the professional asset.", "career", "VI"),
    ("AmatyaKaraka", "Mars", None, None, "Career in military, engineering, sports, or surgery. Action and courage define profession.", "career", "VI"),
    ("AmatyaKaraka", "Saturn", None, None, "Career in government, law, administration, or social service. Discipline and patience are professional keys.", "career", "VI"),
    ("DaraKaraka", "Venus", None, None, "Spouse is charming, artistic, and loving. Marriage is beautiful and fulfilling.", "relationship", "VI"),
    ("DaraKaraka", "Jupiter", None, None, "Spouse is wise, educated, and spiritual. Marriage brings wisdom and expansion.", "relationship", "VI"),
    ("DaraKaraka", "Mercury", None, None, "Spouse is intelligent, communicative, and clever. Intellectual partnership.", "relationship", "VI"),
    ("DaraKaraka", "Moon", None, None, "Spouse is nurturing, emotional, and homemaking. Emotionally rich marriage.", "relationship", "VI"),
    ("DaraKaraka", "Mars", None, None, "Spouse is energetic, bold, and action-oriented. Passionate but possibly conflicted marriage.", "relationship", "VI"),
    ("DaraKaraka", "Saturn", None, None, "Spouse is serious, mature, or older. Karmic marriage with deep commitment.", "relationship", "VI"),
    ("PutraKaraka", "Jupiter", None, None, "Children are wise, spiritual, and fortunate. Jupiter as PK blesses with good progeny.", "relationship", "VI"),
    ("PutraKaraka", "Moon", None, None, "Children are emotionally sensitive and creative. Nurturing relationship with children.", "relationship", "VI"),
    ("GnaatiKaraka", "Mars", None, None, "Rivals are aggressive, competitive, and action-oriented. Conflicts can be intense.", "general", "VI"),
    ("GnaatiKaraka", "Saturn", None, None, "Rivals are persistent, slow-acting but long-term adversaries. Karmic enemies from past lives.", "general", "VI"),
    ("BhatriKaraka", "Mars", None, None, "Siblings are energetic, competitive, and bold. Sibling relationships are dynamic.", "relationship", "VI"),
    ("BhatriKaraka", "Mercury", None, None, "Siblings are intelligent and communicative. Good intellectual relationship with siblings.", "relationship", "VI"),
]

ARGALA_RULES = [
    ("Primary", 2, "benefic", "Benefic argala from 2nd — provides sustenance and basic ingredients for the signification to flourish. Adds wealth, speech, and family support.", "Jupiter in 2nd from lagna provides financial sustenance to self (lagna).", "VI"),
    ("Primary", 2, "malefic", "Malefic argala from 2nd — creates obstacles, harsh speech, or financial obstacles to the signification.", "Saturn in 2nd from lagna creates speech and family hardships.", "VI"),
    ("Primary", 4, "benefic", "Benefic argala from 4th — drives mood, comfort, and progress of the signification. Emotional and domestic support.", "Moon in 4th from lagna provides emotional comfort and mother's support to self.", "VI"),
    ("Primary", 4, "malefic", "Malefic argala from 4th — creates domestic discomfort, emotional suppression, or mother's difficulties.", "Mars in 4th from 10th house creates aggression and conflict in career environment.", "VI"),
    ("Primary", 11, "benefic", "Benefic argala from 11th — provides gains, income, and fulfillment for the signification. Social network supports.", "Jupiter in 11th from lagna provides financial gains to self through wisdom.", "VI"),
    ("Primary", 11, "malefic", "Malefic argala from 11th — gains are blocked or come through struggle. Social circle is adversarial.", "Saturn in 11th from Moon creates delayed emotional fulfillment.", "VI"),
    ("Secondary", 5, "benefic", "Secondary benefic argala from 5th — provides creative, intellectual, and past-merit support to signification.", "Jupiter in 5th from 7th (i.e., 11th house) provides wisdom and good fortune to marriage.", "VI"),
    ("Virodha", 12, "any", "Virodhaargala (obstruction) from 12th cancels argala from 2nd if equal or stronger in planet count/strength.", "If 3 malefics are in 12th and only 1 benefic in 2nd, 12th planet obstructs 2nd benefic argala.", "VI"),
    ("Virodha", 10, "any", "Virodhaargala from 10th cancels argala from 4th.", "Malefics in 10th obstruct comfort and domestic happiness from 4th house.", "VI"),
    ("Virodha", 3, "malefic", "Multiple malefics in 3rd CAUSE argala (not obstruction) — exception to normal virodha rule.", "3 malefics in 3rd from lagna create strong argala for courage and initiative.", "VI"),
    ("Virodha", 9, "any", "Virodhaargala from 9th cancels secondary argala from 5th.", "Saturn in 9th can cancel creative blessing from Jupiter in 5th if stronger.", "VI"),
]

NEECHA_BHANGA_RULES = [
    ("Planet causing debilitation is in kendra from lagna or Moon", "Debilitation is cancelled. Native rises from low station to great heights.", "Neecha Bhanga Raja Yoga", "K"),
    ("Lord of debilitation sign is in kendra from lagna", "Debilitation cancelled. Planet gives strongly positive results despite technical weakness.", "Neecha Bhanga Raja Yoga", "K"),
    ("Planet that gets exalted in the debilitation sign is in kendra from lagna", "Debilitation cancelled. The counteracting exalted planet neutralizes weakness.", "Neecha Bhanga Raja Yoga", "K"),
    ("Debilitated planet is aspected by its exaltation lord", "Debilitation substantially reduced. Native still achieves positive results in planet's domain.", "Neecha Bhanga (partial)", "K"),
    ("Debilitated planet is in exaltation navamsa (D9)", "Debilitation significantly reduced. Planet is weak in rasi but strong in navamsa — hidden strength.", "Neecha Bhanga (partial via navamsa)", "VI"),
    ("Multiple planets cause Neecha Bhanga for each other", "Cross-cancellation creates a powerful Raja Yoga. Exceptional rise from humble origins.", "Neecha Bhanga Raja Yoga (double)", "K"),
]

TRANSIT_RULES = [
    ("Saturn", None, 30, "When Saturn transits a rasi with 30+ SAV rekhas — results are mostly positive, life moves forward smoothly.", "Saturn's 7.5-year transit (sade sati) over Moon: avoid major decisions in middle phase.", "VI"),
    ("Saturn", None, 20, "When Saturn transits a rasi with 20-29 SAV rekhas — mixed results, both opportunities and obstacles.", "Check dasha period simultaneously for better accuracy.", "VI"),
    ("Saturn", None, 0, "When Saturn transits a rasi with below 20 SAV rekhas — difficulties, delays, and obstructions predominate.", "Propitiate Saturn, increase service activities, avoid new ventures.", "VI"),
    ("Jupiter", None, 30, "Jupiter transiting strong SAV rasi brings expansion, wealth, and opportunities in related life areas.", "Jupiter's one-year transit marks key expansion periods.", "VI"),
    ("Jupiter", None, 20, "Jupiter in average SAV rasi gives moderate positive results with some mixed outcomes.", None, "VI"),
    ("Rahu", None, 0, "Rahu transiting weak SAV rasi causes obsessions, sudden events, and disruptions in related areas.", "Rahu 18-month transit is most impactful for sudden changes.", "VI"),
    ("Sun", None, 30, "Sun transiting strong SAV rasi brings recognition, energy, and authority in related house matters.", "Sun's 30-day monthly transit activates the house's affairs.", "VI"),
]

# ─────────────────────────────────────────────────────────────────────────────
# BUILD DATABASE
# ─────────────────────────────────────────────────────────────────────────────
def build_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Drop and recreate tables
    for table in ["lagna_lord_rules","house_lord_in_house","yogas","special_rules",
                   "disease_yogas","dasha_effects","special_lagna_rules",
                   "chara_karaka_effects","argala_rules","neecha_bhanga_rules","transit_rules"]:
        c.execute(f"DROP TABLE IF EXISTS {table}")
    conn.commit()

    for stmt in SCHEMA.strip().split("CREATE TABLE"):
        if stmt.strip():
            c.execute("CREATE TABLE" + stmt)
    conn.commit()

    # Insert data
    c.executemany("INSERT INTO lagna_lord_rules (lagna_lord_house,condition,effect,category,sentiment,source) VALUES (?,?,?,?,?,?)", LAGNA_LORD_RULES)
    c.executemany("INSERT INTO house_lord_in_house (lord_of_house,placed_in_house,effect,category,sentiment,source) VALUES (?,?,?,?,?,?)", HOUSE_LORD_IN_HOUSE)
    c.executemany("INSERT INTO yogas (name,yoga_type,condition_rule,planets_involved,effect,strength,source) VALUES (?,?,?,?,?,?,?)", YOGAS)
    c.executemany("INSERT INTO special_rules (rule_type,condition,effect,sentiment,source) VALUES (?,?,?,?,?)", SPECIAL_RULES)
    c.executemany("INSERT INTO disease_yogas (body_part,organ_system,condition,planets_involved,houses_involved,effect,remedy,source) VALUES (?,?,?,?,?,?,?,?)", DISEASE_YOGAS)
    c.executemany("INSERT INTO dasha_effects (dasha_planet,placement_house,sign_nature,general_effects,wealth_effects,health_effects,relationship_effects,career_effects,source) VALUES (?,?,?,?,?,?,?,?,?)", DASHA_EFFECTS)
    c.executemany("INSERT INTO special_lagna_rules (lagna_type,aspect_house,planet,condition,effect,category,source) VALUES (?,?,?,?,?,?,?)", SPECIAL_LAGNA_RULES)
    c.executemany("INSERT INTO chara_karaka_effects (karaka,karaka_planet,house_in_rasi,sign,effect,category,source) VALUES (?,?,?,?,?,?,?)", CHARA_KARAKA_EFFECTS)
    c.executemany("INSERT INTO argala_rules (argala_type,from_position,planet_nature,effect_on_reference,example,source) VALUES (?,?,?,?,?,?)", ARGALA_RULES)
    c.executemany("INSERT INTO neecha_bhanga_rules (condition,effect,yoga_name,source) VALUES (?,?,?,?)", NEECHA_BHANGA_RULES)
    c.executemany("INSERT INTO transit_rules (planet,transit_house,ashtakavarga_min,effect,timing_notes,source) VALUES (?,?,?,?,?,?)", TRANSIT_RULES)

    conn.commit()
    conn.close()

    # Report counts
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    tables = ["lagna_lord_rules","house_lord_in_house","yogas","special_rules",
              "disease_yogas","dasha_effects","special_lagna_rules",
              "chara_karaka_effects","argala_rules","neecha_bhanga_rules","transit_rules"]
    total = 0
    for t in tables:
        n = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t}: {n} rows")
        total += n
    conn.close()
    print(f"\n✅ Database built at {DB_PATH} — {total} total knowledge rows")

if __name__ == "__main__":
    build_db()
