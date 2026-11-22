"""Job queue and worker (docs/design/admin-and-sync.md, sections 2 and 3).

The web process only enqueues jobs and reads their progress; `python -m north.jobs.worker`
claims and runs them. Kinds and schedules are declared in code by country modules (registry).
"""
