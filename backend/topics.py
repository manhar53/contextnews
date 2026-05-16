"""AFPA-style "important" lecturette / GD topics — full 94 set (84 from the
PDF + 5 each from the two practice schedule slides).

Used to auto-prioritise which articles get LLM deep analysis in the
background, so common SSB lecturette/GD topics are always pre-analysed.

Keyword discipline: only specific multi-word phrases or unambiguous proper
nouns. Short ambiguous tokens ('lac', 'scs', 'us' alone, etc.) are avoided
to keep substring matching precise — see the earlier 'rep_lac_e' incident.
"""

IMPORTANT_TOPICS: dict[str, list[str]] = {
    # ─── Schedule slide 1 — Indo-bilaterals + multilateralism ─────────
    "Indo-US Relations": [
        "indo-us", "indo us", "india us", "india-us", "us india", "us-india",
        "modi biden", "biden modi", "modi trump", "trump modi", "modi obama",
        "2+2 dialogue", "washington delhi", "delhi washington",
        "india washington",
    ],
    "Indo-Russia Relations": [
        "india russia", "india-russia", "russia india", "russia-india",
        "modi putin", "putin modi", "s-400", "brahmos", "rosatom india",
        "kudankulam", "russian crude india",
    ],
    "Indo-China Relations": [
        "india china", "india-china", "china india", "china-india",
        "ladakh", "galwan", "doklam", "tawang", "arunachal pradesh",
        "india china border", "modi xi", "xi modi",
    ],
    "Indo-Bangladesh Relations": [
        "bangladesh india", "india bangladesh", "india-bangladesh",
        "bangladesh-india", "dhaka delhi", "delhi dhaka",
        "teesta", "sheikh hasina", "yunus bangladesh",
    ],
    "Global South / Multilateralism": ["global south", "multilateralism", "g77", "g-77"],

    # ─── Schedule slide 2 — Wars / energy / UN / global economy ───────
    "US-Israel & Iran War": [
        "israel iran", "iran israel", "israeli strike", "iranian strike",
        "gaza", "hamas", "hezbollah", "idf", "strait of hormuz", "houthi",
    ],
    "Russia-Ukraine Conflict": [
        "russia ukraine", "ukraine russia", "putin", "zelensky",
        "kyiv", "donbas", "kursk", "ukraine war",
    ],
    "Energy Security": [
        "energy security", "opec", "crude oil", "lng", "petroleum import",
        "oil prices", "world energy crisis",
    ],
    "UN: Relevance & Alternatives": [
        "united nations", "un security council", "unsc", "unga",
        "g20 summit", "brics summit", "sco summit",
    ],
    "Challenges to Global Economy": [
        "global economy", "global recession", "trade war", "tariff war",
        "supply chain", "imf forecast", "world bank report",
    ],

    # ─── PDF: Defence & Strategic ──────────────────────────────────────
    "AFSPA": ["afspa", "armed forces special powers"],
    "FDI in Defence Sector": ["fdi in defence", "defence fdi", "defence foreign investment"],
    "Defence Budget": ["defence budget", "defense budget", "indian defence allocation"],
    "DRDO / Indian Missile Program": [
        "drdo", "agni missile", "prithvi missile", "brahmos", "tejas",
        "akash missile", "agni-v", "k-15 missile",
    ],
    "Indian Foreign Policy": [
        "indian foreign policy", "india foreign policy", "external affairs minister",
        "jaishankar", "mea india",
    ],
    "Cross Border Terrorism": [
        "cross border terrorism", "cross-border terrorism",
        "pakistan sponsored terror", "pulwama", "uri attack",
    ],
    "Coastal Security": ["coastal security", "indian navy", "naval security", "indian coast guard"],
    "Nuclear Proliferation": ["nuclear proliferation", "npt", "nuclear weapon", "n-deal"],
    "Nuclear Power": [
        "nuclear power plant", "nuclear energy", "small modular reactor",
        "civil nuclear", "kudankulam",
    ],
    "Indian Missile Program": ["indian missile programme", "indian missile program", "agni-vi"],
    "Arms Race": ["arms race", "hypersonic missile", "icbm"],
    "Indo-Pacific": ["indo-pacific", "indo pacific", "quad summit", "aukus"],
    "Afghanistan-Implications for India": [
        "afghanistan", "taliban", "kabul",
    ],
    "NATO and its Relevance": ["nato", "north atlantic treaty"],
    "China-Taiwan": ["taiwan", "taipei", "tsai ing-wen", "strait of taiwan"],
    "South China Sea": ["south china sea"],
    "West Asia Crisis": ["west asia", "middle east crisis"],
    "Internal Situation of Pakistan": [
        "pakistan economic crisis", "pakistan inflation",
        "imran khan", "shehbaz sharif", "pakistan default",
    ],
    "CPEC": ["cpec", "china pakistan economic"],
    "Make in India": ["make in india", "atmanirbhar", "self-reliance defence"],
    "ISRO": ["isro", "chandrayaan", "gaganyaan", "aditya-l1", "vikram sarabhai"],
    "Coastal & Border Security": ["border security force", "bsf", "border management india"],
    "Agniveer / Agnipath": ["agniveer", "agnipath"],

    # ─── PDF: Internal Security ───────────────────────────────────────
    "Terrorism": ["terror attack india", "terror plot", "terror funding"],
    "ISIS": ["isis", "islamic state", "is-k", "isis-k"],
    "Naxalism": ["naxal", "maoist", "left wing extremism"],
    "Religious Fundamentalism": ["religious fundamentalism", "communalism", "communal violence"],
    "Cyber Crime / Security": ["cyber crime", "cyber security", "cyber attack", "ransomware"],
    "NDRF": ["ndrf", "national disaster response"],

    # ─── PDF: Economy ──────────────────────────────────────────────────
    "Indian Economy": ["indian economy", "india gdp", "rbi monetary policy", "inflation in india"],
    "Falling value of Indian Rupee": ["rupee depreciation", "rupee fall", "rupee against dollar"],
    "Tax Reforms": ["tax reform", "gst council", "income tax slab", "direct tax code", "new tax regime"],
    "WTO": ["wto", "world trade organization"],
    "World Bank": ["world bank"],
    "World Trade Organization": ["world trade organisation", "wto ministerial"],
    "World Energy Crisis": ["world energy crisis", "global energy crisis"],
    "E-Commerce": ["e-commerce", "ecommerce", "online retail india", "ondc"],
    "Biotechnology": ["biotechnology", "biotech india", "stem cell research"],
    "Genetically Modified Food": ["gm crop", "genetically modified", "bt brinjal", "gmo crop"],
    "Tourism in India": ["tourism india", "indian tourism", "incredible india"],
    "Sponsorship in Sports": ["sports sponsorship", "sponsorship in sports"],
    "Paid Media": ["paid media", "paid news"],
    "Poverty Eradication": ["poverty eradication", "multidimensional poverty", "poverty line india"],
    "Brain Drain": ["brain drain", "indian diaspora migration"],

    # ─── PDF: Society ─────────────────────────────────────────────────
    "Juvenile Crime": ["juvenile crime", "juvenile justice", "child in conflict with law"],
    "Sex Education": ["sex education", "comprehensive sexuality education"],
    "Reservation System": ["reservation system", "obc reservation", "caste reservation", "ews quota"],
    "Honor Killing": ["honour killing", "honor killing"],
    "Dowry System": ["dowry death", "dowry system", "dowry harassment"],
    "Role of NGOs": ["fcra", "civil society organisation", "ngo crackdown"],
    "Senior Citizens": ["senior citizens", "elderly care", "old age pension"],
    "Capital Punishment": ["death penalty", "capital punishment", "death row india"],
    "Child Labour": ["child labour", "child labor"],
    "Women Empowerment": ["women empowerment", "gender equality india", "beti bachao", "nari shakti"],
    "Higher Education in India": ["higher education", "ugc", "nep 2020", "national education policy", "neet exam"],
    "Mercy Killing": ["mercy killing", "euthanasia", "passive euthanasia"],
    "Justice Delayed is Justice Denied": ["pendency of cases", "judicial backlog", "case pendency"],
    "Influence of Western Culture": ["western culture", "westernisation", "cultural homogenisation"],
    "Sports in India": ["khelo india", "olympics india", "asian games india"],
    "Swach Bharat Abhiyaan": ["swachh bharat", "swach bharat", "clean india mission"],
    "Rural Development in India": ["mgnrega", "rural development", "panchayati raj"],
    "Right to Education (RTE)": ["right to education", "rte act"],
    "Secularism": ["secularism", "uniform civil code", "ucc india"],
    "Family Planning": ["family planning", "population policy", "fertility rate india"],
    "Organ Trafficking": ["organ trafficking", "kidney trade", "illegal organ trade"],
    "Division of States": ["state reorganisation", "telangana formation", "andhra pradesh bifurcation", "ladakh union territory"],
    "Fundamental Rights": ["fundamental rights", "right to privacy", "puttaswamy judgement"],
    "Organic Farming": ["organic farming", "natural farming", "zero budget farming"],

    # ─── PDF: Governance & Polity ──────────────────────────────────────
    "Indian Democracy": ["indian democracy", "supreme court of india", "election commission of india"],
    "Constitutional Reforms": ["constitutional reform", "constitutional amendment india"],
    "CAA / NRC": ["caa", "nrc", "citizenship amendment"],
    "Farm Bill / Laws": ["farm law", "farm bill", "msp guarantee", "kisan andolan"],
    "Dynastic Politics": ["dynastic politics", "political dynasty india"],
    "Coalition Politics": ["coalition politics", "coalition government india", "nda alliance", "india alliance"],

    # ─── PDF: International ────────────────────────────────────────────
    "Arab Spring": ["arab spring", "tunisia uprising", "egyptian revolution"],
    "Reforms in UN Security Council": ["unsc reform", "permanent seat", "p5 expansion", "india unsc bid"],
    "Role of India in United Nations": ["india at un", "india unga", "india unsc rotating"],
    "India's Role in World Forum": ["india g20 presidency", "india at brics", "india at davos"],
    "Sri Lankan Crisis": ["sri lanka crisis", "colombo crisis", "rajapaksa", "wickremesinghe"],
    "Soft Power": ["soft power india", "yoga diplomacy", "vaccine diplomacy"],
    "Changing World Order": ["changing world order", "new world order"],
    "Emergence of Multipolar World": ["multipolar world", "multipolarity", "brics expansion"],
    "Global Uncertainties": ["geopolitical uncertainty", "global uncertainty", "global instability"],
    "Climate Change Strategic": ["cop28", "cop29", "climate change", "net zero india", "renewable energy india"],
    "Farm laws Boon or Bane": ["farm laws boon", "farm laws bane"],
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
