"""Irish places used to read the lists' addresses (record 0008, slice E2). Pure data.

Counties are ISO 3166-2:IE codes (local part). Towns are the ones that appear in the ILEP and
TrustEd addresses (and a few large towns), each with its county; a town not listed here is
never guessed: the campus city stays unknown.
"""

from __future__ import annotations

COUNTIES: dict[str, str] = {
    "CW": "Carlow", "CN": "Cavan", "CE": "Clare", "CO": "Cork", "DL": "Donegal", "D": "Dublin",
    "G": "Galway", "KY": "Kerry", "KE": "Kildare", "KK": "Kilkenny", "LS": "Laois",
    "LM": "Leitrim", "LK": "Limerick", "LD": "Longford", "LH": "Louth", "MO": "Mayo",
    "MH": "Meath", "MN": "Monaghan", "OY": "Offaly", "RN": "Roscommon", "SO": "Sligo",
    "TA": "Tipperary", "WD": "Waterford", "WH": "Westmeath", "WX": "Wexford", "WW": "Wicklow",
}
COUNTY_BY_NAME: dict[str, str] = {name.lower(): code for code, name in COUNTIES.items()}

# Town as written in the served data -> county code.
TOWNS: dict[str, str] = {
    "Dublin": "D", "Dun Laoghaire": "D", "Malahide": "D", "Swords": "D", "Tallaght": "D",
    "Blackrock": "D", "Cork": "CO", "Schull": "CO", "Galway": "G", "Limerick": "LK",
    "Waterford": "WD", "Drogheda": "LH", "Dundalk": "LH", "Bray": "WW", "Athlone": "WH",
    "Tralee": "KY", "Killarney": "KY", "Cahersiveen": "KY", "Naas": "KE", "Maynooth": "KE",
    "Wexford": "WX", "Sligo": "SO", "Carlow": "CW", "Kilkenny": "KK", "Letterkenny": "DL",
    "Bundoran": "DL", "Ennis": "CE", "Castlebar": "MO", "Clonmel": "TA", "Thurles": "TA",
}
# Other spellings found in addresses -> the town name above.
TOWN_SPELLINGS: dict[str, str] = {"dún laoghaire": "Dun Laoghaire"}

# Eircode routing keys of Dublin city's postal districts (D01-D24, D6W).
DUBLIN_ROUTING_KEYS: frozenset[str] = frozenset({f"D{n:02d}" for n in range(1, 25)} | {"D6W"})
