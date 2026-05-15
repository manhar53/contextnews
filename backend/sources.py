"""Layer 1: source credibility priority (0-10).

Higher score => higher in the feed. Matched by exact source name first,
then by a substring key so GDELT domains (e.g. "thehindu.com") also score.
"""

# exact source-name -> score
SOURCE_PRIORITY: dict[str, int] = {
    "IDSA": 10,
    "PIB India": 10,
    "The Print Defence": 9,
    "Indian Defence Review": 9,
    "The Hindu": 8,
    "Reuters": 8,
    "BBC News": 7,
    "ANI News": 7,
    "Indian Express": 7,   # credible national (not in spec list; reasonable default)
    "Hindustan Times": 6,
    "NDTV India": 6,
    "Al Jazeera": 6,
}

# substring (lowercased) -> score, for NewsAPI/GDELT domains & name variants
_SUBSTRING_PRIORITY: list[tuple[str, int]] = [
    ("idsa", 10),
    ("pib.gov", 10),
    ("theprint", 9),
    ("indiandefencereview", 9),
    ("thehindu", 8),
    ("reuters", 8),
    ("bbc", 7),
    ("aninews", 7),
    ("ani news", 7),
    ("indianexpress", 7),
    ("hindustantimes", 6),
    ("ndtv", 6),
    ("aljazeera", 6),
    ("al jazeera", 6),
]

DEFAULT_PRIORITY = 5


def get_priority(source: str | None) -> int:
    if not source:
        return DEFAULT_PRIORITY
    if source in SOURCE_PRIORITY:
        return SOURCE_PRIORITY[source]
    key = source.lower()
    for needle, score in _SUBSTRING_PRIORITY:
        if needle in key:
            return score
    return DEFAULT_PRIORITY
