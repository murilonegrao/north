"""Domain core: filter, score, cost and risk. Pure Python, no I/O.

Dependency rule (UML section 6): nothing here imports from ``north.api``,
``north.repository``, ``north.ingest`` or ``north.extract``. The core knows no
country and talks to ``domain.countries.<country>`` through the CountryRules interface.
"""
