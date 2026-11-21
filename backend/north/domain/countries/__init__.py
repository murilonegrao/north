"""Country rule modules (C-09) behind one interface. Only ``us`` is implemented.

The core (API, filters, facets) asks this registry for a country's rules instead of importing
a country module or naming a country: the CIP scope families, the STEM rule key, the subdivision
id format and the ids of the source files behind a program's values.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from north.domain.countries.us import cip as us_cip
from north.domain.countries.us import stem as us_stem
from north.domain.countries.us import subdivisions as us_subdivisions


@dataclass(frozen=True)
class CountryRules:
    code: str  # ISO 3166-1 alpha-2
    cip_families: Mapping[str, str]  # scope family key -> code prefix, in display order
    cip_family: Callable[[str], str | None]
    stem_rule_key: str
    subdivisions: frozenset[str]  # local subdivision codes ("TX")
    program_sources: tuple[str, ...]  # source ids behind a program's values (contract v0.1 §5)
    currency: str  # ISO 4217 code of tuition amounts

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
}
# Used when a subdivision code belongs to no registered country: its filter then matches nothing.
DEFAULT_COUNTRY = "US"


def rules_for(country_code: str) -> CountryRules:
    """Rules of a registered country; KeyError for a country North does not cover."""
    return _REGISTRY[country_code.upper()]


def country_of_subdivision(local: str) -> str:
    """Country code of a local subdivision code ("TX" -> "US"), or DEFAULT_COUNTRY."""
    code = local.upper()
    for rules in _REGISTRY.values():
        if code in rules.subdivisions:
            return rules.code
    return DEFAULT_COUNTRY


def country_of_subdivision_id(subdivision_id: str) -> str:
    """Country code of a stored subdivision id ("US-TX" -> "US")."""
    return subdivision_id.split("-", 1)[0].upper()
