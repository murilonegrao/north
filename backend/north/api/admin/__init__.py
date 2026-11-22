"""Admin API under /api/admin (record 0006). Every route requires a session except login."""

from fastapi import APIRouter

from north.api.admin import audit, auth, institutions, jobs, overview, uploads, users

router = APIRouter(prefix="/api/admin", include_in_schema=False)
for module in (auth, overview, jobs, uploads, users, audit, institutions):
    router.include_router(module.router)
