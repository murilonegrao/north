"""UML section 6: the domain imports nothing from api, repository, ingest or extract."""

import ast
from pathlib import Path

import north

FORBIDDEN = ("north.api", "north.repository", "north.ingest", "north.extract")
DOMAIN = Path(north.__file__).parent / "domain"


def test_domain_has_no_outward_imports() -> None:
    offenders = []
    for file in DOMAIN.rglob("*.py"):
        for node in ast.walk(ast.parse(file.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            else:
                continue
            offenders += [f"{file}: {n}" for n in names if n.startswith(FORBIDDEN)]
    assert offenders == []
