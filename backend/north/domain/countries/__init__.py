"""Country rule modules (C-09) behind one interface: ``us`` and ``ie`` (record 0008).

The core (API, filters, facets) asks this registry for a country's rules instead of importing
a country module or naming a country: the CIP scope families, the STEM rule key, the subdivision
id format, the ids of the source files behind a program's values, the notes attached to an
authorization scheme, and the country criteria (authorization, family).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from north.domain.countries.ie import places as ie_places
from north.domain.countries.ie import rules as ie_rules
from north.domain.countries.us import cip as us_cip
from north.domain.countries.us import stem as us_stem
from north.domain.countries.us import subdivisions as us_subdivisions


@dataclass(frozen=True)
class CountryRules:
    code: str  # ISO 3166-1 alpha-2
    cip_families: Mapping[str, str]  # scope family key -> code prefix, in display order
    cip_family: Callable[[str], str | None]
    stem_rule_key: str | None  # None: the country has no STEM rule
    subdivisions: frozenset[str]  # local subdivision codes ("TX")
    program_sources: tuple[str, ...]  # source ids behind a program's values (contract v0.1 §5)
    currency: str  # ISO 4217 code of tuition amounts
    # True when a city name is one place in the whole country, so city facets need no state.
    cities_unique: bool = False
    # Notes (migration rules) shown next to a program-level authorization of a scheme.
    authorization_notes: Callable[[str], list[dict[str, Any]]] = lambda scheme: []
    # Country criteria (record 0008/T2, T5); None until the module implements them.
    authorization: Callable[..., Any] | None = None
    family: Callable[..., Any] | None = None

    def subdivision_id(self, local: str) -> str:
        """ISO 3166-2 style id stored in the database: ``<country>-<local>``."""
        return f"{self.code}-{local.upper()}"

    @staticmethod
    def local_subdivision(subdivision_id: str) -> str:
        return subdivision_id.split("-", 1)[-1]


_REGISTRY: dict[str, CountryRules] = {
    "US": CountryRules(
        code="US",
        cip_families=us_cip.FAMILIES,
        cip_family=us_cip.cip_family,
        stem_rule_key=us_stem.RULE_KEY,
        subdivisions=us_subdivisions.CODES,
        program_sources=("ipeds_hd", "ipeds_c_a", "ipeds_ic_ay", "dhs_stem_list", "sevp_csl",
                         "dapip"),
        currency="USD",
    ),
    "IE": CountryRules(
        code="IE",
        cip_families={},
        cip_family=lambda code: None,
        stem_rule_key=None,
        subdivisions=frozenset(ie_places.COUNTIES),
        program_sources=("ie_ilep", "ie_trusted"),
        currency="EUR",
        cities_unique=True,
        authorization_notes=ie_rules.rule_notes,
        authorization=ie_rules.authorization,
        family=ie_rules.family,
    ),
}
# Used when a subdivision code belongs to no registered country: its filter then matches nothing.
DEFAULT_COUNTRY = "US"


def rules_for(country_code: str) -> CountryRules:
    """Rules of a registered country; KeyError for a country North does not cover."""
    return _REGISTRY[country_code.upper()]


def is_country(country_code: str) -> bool:
    return country_code.upper() in _REGISTRY


def country_of_subdivision(local: str) -> str:
    """Country code of a local subdivision code ("TX" -> "US"), or DEFAULT_COUNTRY. A code
    used by two countries ("CO": Colorado, Cork) resolves to the first registered (US); the
    API takes an explicit ``country`` to say otherwise."""
    code = local.upper()
    for rules in _REGISTRY.values():
        if code in rules.subdivisions:
            return rules.code
    return DEFAULT_COUNTRY


def country_of_subdivision_id(subdivision_id: str) -> str:
    """Country code of a stored subdivision id ("US-TX" -> "US")."""
    return subdivision_id.split("-", 1)[0].upper()
