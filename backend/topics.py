"""AFPA-style "important" lecturette / GD topics (from the academy's list +
schedule slides). Used to auto-prioritise which articles get Gemini deep
analysis in the background, so common SSB topics are always pre-analysed.
"""

# topic_name -> list of lowercase substring keywords. ANY hit -> important.
IMPORTANT_TOPICS: dict[str, list[str]] = {
    # Schedule slide 1 — Indo-bilaterals + multilateralism
    "Indo-US Relations": ["indo-us", "india us", "india-us", "modi biden", "modi trump", "2+2 dialogue"],
    "Indo-Russia Relations": ["india russia", "india-russia", "modi putin", "s-400", "brahmos"],
    "Indo-China Relations": ["india china", "india-china", "lac", "ladakh", "galwan", "doklam", "border talks", "xi jinping"],
    "Indo-Bangladesh Relations": ["bangladesh", "dhaka", "teesta", "hasina", "yunus"],
    "Global South / Multilateralism": ["global south", "multilateralism", "g77", "g-77"],

    # Schedule slide 2 — Wars / energy / UN / global economy
    "US-Israel & Iran War": ["israel", "iran", "gaza", "hamas", "hezbollah", "idf", "strait of hormuz", "houthi"],
    "Russia-Ukraine Conflict": ["russia ukraine", "ukraine", "putin", "zelensky", "kyiv", "donbas", "kursk"],
    "Energy Security": ["energy security", "opec", "crude oil", "lng", "petroleum import", "oil prices"],
    "UN: Relevance & Alternatives": ["united nations", "un security council", "unsc", "unga", "g20", "brics", "sco"],
    "Challenges to Global Economy": ["global economy", "global recession", "trade war", "tariff", "supply chain", "imf", "world bank"],

    # Core AFPA "84 topics" (current-affairs subset most relevant for ranking)
    "AFSPA": ["afspa", "armed forces special powers"],
    "FDI in Defence": ["fdi in defence", "defence fdi"],
    "CPEC": ["cpec", "china pakistan economic"],
    "WTO": ["wto", "world trade organization"],
    "World Bank": ["world bank"],
    "Indian Economy": ["indian economy", "india gdp", "rbi", "inflation in india"],
    "Defence Budget": ["defence budget", "defense budget"],
    "ISRO": ["isro", "chandrayaan", "gaganyaan", "aditya-l1"],
    "DRDO / Missile Program": ["drdo", "agni missile", "prithvi missile", "brahmos", "tejas", "akash missile"],
    "ISIS / Terrorism": ["isis", "islamic state", "terror attack", "terrorism", "cross-border terrorism"],
    "Naxalism": ["naxal", "maoist", "lwe", "left wing extremism"],
    "Make in India": ["make in india", "atmanirbhar", "self-reliance defence"],
    "Cyber Crime / Security": ["cyber crime", "cyber security", "cyber attack", "ransomware"],
    "Indian Foreign Policy": ["indian foreign policy", "india foreign policy", "external affairs minister", "jaishankar"],
    "Coastal Security": ["coastal security", "indian navy", "naval security"],
    "Nuclear Proliferation": ["nuclear proliferation", "npt", "nuclear weapon", "n-deal"],
    "CAA / NRC": ["caa", "nrc", "citizenship amendment"],
    "Farm Laws / Bill": ["farm law", "farm bill", "msp", "kisan andolan"],
    "Agniveer / Agnipath": ["agniveer", "agnipath"],
    "Afghanistan Implications": ["afghanistan", "taliban", "kabul"],
    "NATO Relevance": ["nato", "north atlantic treaty"],
    "Indo-Pacific": ["indo-pacific", "indo pacific", "quad", "aukus"],
    "China-Taiwan": ["taiwan", "taipei", "tsai", "strait of taiwan"],
    "Changing World Order / Multipolar": ["multipolar", "world order", "brics expansion"],
    "Sri Lankan Crisis": ["sri lanka", "colombo", "rajapaksa", "wickremesinghe"],
    "Soft Power": ["soft power", "yoga diplomacy", "vaccine diplomacy"],
    "Arms Race": ["arms race", "hypersonic", "icbm"],
    "Indian Democracy / Constitution": ["constitutional reform", "indian democracy", "supreme court of india"],
    "Climate / Environment Strategic": ["cop28", "cop29", "climate change", "net zero", "renewable energy india"],
    "South China Sea": ["south china sea", "scs"],
    "West Asia Crisis": ["west asia", "middle east crisis"],
}

# Flat (keyword, topic) pairs for fast scanning.
_PAIRS: list[tuple[str, str]] = [
    (kw, name) for name, kws in IMPORTANT_TOPICS.items() for kw in kws
]


def _slug(name: str) -> str:
    import re

    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "topic"


# slug -> {"name": original, "keywords": [...]}
TOPICS_BY_SLUG: dict[str, dict] = {
    _slug(name): {"name": name, "keywords": kws}
    for name, kws in IMPORTANT_TOPICS.items()
}


def topic_index() -> list[dict]:
    return [
        {"slug": s, "name": v["name"], "keywords": v["keywords"]}
        for s, v in TOPICS_BY_SLUG.items()
    ]


def match_topics(text: str) -> list[str]:
    if not text:
        return []
    t = text.lower()
    hits: list[str] = []
    seen: set[str] = set()
    for kw, name in _PAIRS:
        if kw in t and name not in seen:
            seen.add(name)
            hits.append(name)
    return hits


def is_important(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return any(kw in t for kw, _ in _PAIRS)
