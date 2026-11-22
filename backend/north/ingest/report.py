"""Counts per subdivision, open reconciliation tasks and the file each source last loaded.

Used by `cli report` and by the admin overview, once per country. Read-only.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

REPORT_SQL = """
select coalesce(i.subdivision_id, i.country_code) as scope,
       count(distinct i.id) as institutions,
       count(distinct i.id) filter (where i.accreditation->>'status' = 'confirmed_official')
           as institutions_accredited,
       count(distinct c.id) filter (where c.intl_authorization->>'status' = 'confirmed_official')
           as campuses_sevp_authorized,
       count(distinct c.id) filter (where c.intl_authorization->>'status' = 'unknown'
                                       or c.intl_authorization is null)
           as campuses_sevp_unknown,
       count(distinct p.id) as programs,
       count(distinct p.id) filter (where pe.result->>'value' = 'true') as programs_stem_opt,
       count(distinct p.id) filter (where p.cost->'graduate_tuition_nonresident'->>'status'
                                       = 'confirmed_official') as programs_with_tuition
from institutions i
left join campuses c on c.institution_id = i.id
left join programs p on p.campus_id = c.id
left join program_eligibilities pe on pe.program_id = p.id
where i.country_code = :country
group by 1
order by 1
"""

FILES_SQL = """
select distinct on (sf.source, r.scope) sf.source, r.scope, sf.file_version, sf.sha256,
       r.finished_at
from ingestion_runs r join source_files sf on sf.id = r.source_file_id
where r.status = 'succeeded' and (r.scope = :country or r.scope like :prefix)
order by sf.source, r.scope, r.finished_at desc
"""

TASKS_SQL = """
select r.scope, t.kind, count(*) as n
from reconciliation_tasks t join ingestion_runs r on r.id = t.run_id
where not t.resolved and (r.scope = :country or r.scope like :prefix)
group by r.scope, t.kind order by r.scope, t.kind
"""


def report(s: Session, country: str = "US") -> dict[str, Any]:
    """Counts per subdivision of ``country``, open reconciliation tasks and the file each
    source last loaded (runs whose scope is the country or one of its subdivisions).

    Two reports (local and production, or before and after a sync) compare with a plain diff.
    """
    params = {"country": country, "prefix": f"{country}-%"}
    states = [dict(r._mapping) for r in s.execute(text(REPORT_SQL), params)]
    tasks: dict[str, dict[str, int]] = {}
    for scope, kind, n in s.execute(text(TASKS_SQL), params):
        tasks.setdefault(scope, {})[kind] = n
    for row in states:
        row["open_tasks"] = tasks.get(row["scope"], {})
    files: dict[str, dict[str, Any]] = {}
    for src, scope, version, sha, _ in s.execute(text(FILES_SQL), params):
        cur = files.setdefault(src, {"file_version": version, "sha256": sha, "scopes": 0})
        if (cur["file_version"], cur["sha256"]) == (version, sha):
            cur["scopes"] += 1
        else:
            cur.setdefault("other_versions", []).append({"scope": scope, "file_version": version,
                                                         "sha256": sha})
    keys = [k for k in states[0] if k not in ("scope", "open_tasks")] if states else []
    total = {k: sum(r[k] for r in states) for k in keys}
    return {"total": {"states": len(states), **total}, "states": states, "source_files": files}
