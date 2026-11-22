"""Parsers for the free-text columns of the ILEP and TrustEd lists (FR-30). Pure functions.

Every parser returns ``None`` when the text does not say the thing plainly; the caller then
stores ``unknown`` with the raw text as evidence (BR-02). Nothing is converted between scales
(an IELTS band is not turned into a CEFR band) and no town is guessed.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from north.domain.cefr import rank
from north.domain.countries.ie.places import (
    COUNTY_BY_NAME,
    DUBLIN_ROUTING_KEYS,
    TOWN_SPELLINGS,
    TOWNS,
)

EXAM_CODES = ("ielts", "cambridge", "trinity", "languagecert", "toefl", "pte", "duolingo", "tie",
              "other")


def clean(value: object) -> str:
    return "" if value is None else re.sub(r"\s+", " ", str(value)).strip()


def norm_title(value: object) -> str:
    """Title key for matching across lists: ASCII, lower case, '&' = 'and', no punctuation."""
    t = unicodedata.normalize("NFKD", clean(value)).encode("ascii", "ignore").decode().lower()
    t = t.replace("&", " and ")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", t).split())


_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"\+?\d[\d ()-]{7,}\d")


def scrub(text: str) -> str:
    """Evidence is public: an email address or a phone number never reaches it (NFR-10)."""
    return _PHONE.sub("[number removed]", _EMAIL.sub("[email removed]", text))


# ------------------------------------------------------------------------------ references

_REF = re.compile(r"^(TE)?(\d{4})\s*/\s*(\d{3,4})$", re.I)


@dataclass(frozen=True)
class Ref:
    value: str  # as written, spaces removed: "0018/0001", "TE0058/0012"
    trusted: bool
    provider_no: str  # 4 digits, no TE prefix (scheme ie_provider_no)
    programme_no: str


def parse_ref(raw: object) -> Ref | None:
    m = _REF.match(clean(raw))
    if not m:
        return None
    te, provider, programme = m.groups()
    value = f"{'TE' if te else ''}{provider}/{programme}"
    return Ref(value, bool(te), provider, programme)


# ------------------------------------------------------------------------------ course facts

_NUMBER = re.compile(r"\d+(?:\.\d+)?")


def parse_weeks(raw: object) -> int | None:
    """'25 weeks', '25+ weeks', '25-28 weeks', '25 week minimum' -> 25 (the first number:
    the minimum length). Plain numbers are read as weeks only in the duration column."""
    text = clean(raw).lower()
    if not text or "ects" in text:
        return None
    m = _NUMBER.search(text)
    if not m or "." in m.group(0):
        return None
    weeks = int(m.group(0))
    return weeks if 1 <= weeks <= 104 else None


def parse_hours(raw: object) -> float | int | None:
    """Hours of class per week: the lowest number written ('15-20 hours' -> 15, '16+ hours' ->
    16, '15 mornings only. 25 including afternoons' -> 15, '21 hours 20 mins' -> 21.33)."""
    text = clean(raw).lower()
    if not text:
        return None
    m = re.fullmatch(r"(\d+)\s*hours?\s*(\d+)\s*min(?:ute)?s?", text)
    if m:
        return round(int(m.group(1)) + int(m.group(2)) / 60, 2)
    numbers = [float(n) for n in _NUMBER.findall(text)]
    if not numbers:
        return None
    low = min(numbers)
    if not 1 <= low <= 60:
        return None
    return int(low) if low.is_integer() else round(low, 2)


# A CEFR band written in the text: A0-A2, B1-B2, C1-C2, optionally with a sub-level (A1.1) or
# a sign (B1+). Letters or digits right next to it disqualify it ("CEFRL B1" counts, "AB12" no).
_BAND = re.compile(r"(?<![A-Za-z0-9])(A[0-2]|B[12]|C[12])(?![0-9])")


def parse_cefr(raw: object) -> tuple[str | None, str | None]:
    """(lowest band, highest band) named in the text, or (None, None).

    'Beginner A1.1' -> (A1, A1); 'A2-C1' -> (A2, C1); 'A1 / A2 / B1 / B2 / C1' -> (A1, C1);
    'IELTS 5.5', 'Beginner', 'B+' -> (None, None): no band is written."""
    found = _BAND.findall(clean(raw).upper())
    if not found:
        return None, None
    ordered = sorted(set(found), key=rank)
    return ordered[0], ordered[-1]



class ExamMap:
    """Awarding-body spelling -> exam code, from ``data/reference/ie_exam_names.csv``."""

    def __init__(self, mapping: dict[str, str]) -> None:
        self._map = mapping

    @staticmethod
    def key(raw: object) -> str:
        return clean(raw).lower()

    @classmethod
    def load(cls, path: Path) -> ExamMap:
        mapping: dict[str, str] = {}
        with path.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                code = row["exam"].strip()
                if code not in EXAM_CODES:
                    raise ValueError(f"{path.name}: unknown exam code {code!r}")
                mapping[cls.key(row["raw"])] = code
        return cls(mapping)

    def code(self, raw: object) -> str | None:
        """The exam code, or None when the spelling is not in the map (add it there)."""
        return self._map.get(self.key(raw))


# ------------------------------------------------------------------------------ places

_EIRCODE = re.compile(r"\b([AC-FHKNPRTV-Y]\d{2}|D6W)\s?[0-9AC-FHKNPRTV-Y]{4}\b", re.I)
_COUNTY = re.compile(r"\b(?:co\.?|county)\s+([A-Za-z]+)", re.I)
_SITES = re.compile(r"\s+/\s*|\s*/\s+")
_TOWN_NAMES = {t.lower(): t for t in TOWNS} | TOWN_SPELLINGS
_TOWN_AT_END = re.compile(
    r"(?:^|\s)(" + "|".join(sorted(map(re.escape, _TOWN_NAMES), key=len, reverse=True))
    + r")(?:\s+(?:city|town))?(?:\s+\d{1,2}w?)?$", re.I)


@dataclass(frozen=True)
class Place:
    city: str | None  # a key of places.TOWNS
    county: str | None  # ISO 3166-2:IE local code ("D", "CO")


def _site(text: str) -> Place:
    """One postal address: the town is the last comma-separated part that ends with a known
    town name ('Dublin 2', 'Cork City', 'Wexford Town'); 'Co. X' gives the county."""
    city = county = None
    for part in reversed([p for p in text.split(",") if p.strip()]):
        part = re.sub(r"\([^)]*\)", " ", part)
        for m in _EIRCODE.finditer(part):
            if county is None and m.group(1).upper() in DUBLIN_ROUTING_KEYS:
                county = "D"
        part = _EIRCODE.sub(" ", part)
        m = _COUNTY.search(part)
        if m and m.group(1).lower() in COUNTY_BY_NAME:
            county = county or COUNTY_BY_NAME[m.group(1).lower()]
            part = part[: m.start()] + " " + part[m.end():]
        part = " ".join(part.replace(".", " ").split())
        found = _TOWN_AT_END.search(part)
        if found:
            city = _TOWN_NAMES[found.group(1).lower()]
            break
    if city is not None:
        county = TOWNS[city]
    return Place(city, county)


def place_of(address: object) -> Place:
    """City and county of a listed address. Several sites ('... Dublin 2 / ... Cork') give a
    city only when they all name the same town, and a county only when they all agree."""
    pieces: list[str] = []
    for piece in (p.strip() for p in _SITES.split(clean(address))):
        if pieces and re.fullmatch(r"\d+[A-Za-z]?", pieces[-1]):  # "33 / 34 Dame Street"
            pieces[-1] = f"{pieces[-1]}/{piece}"
        elif piece:
            pieces.append(piece)
    sites = [_site(p) for p in pieces]
    if not sites:
        return Place(None, None)
    cities = {s.city for s in sites}
    counties = {s.county for s in sites}
    city = cities.pop() if len(cities) == 1 else None
    county = counties.pop() if len(counties) == 1 else None
    return Place(city, county)
