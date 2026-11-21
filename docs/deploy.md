# Deploying North

How North goes to production on the k3s cluster, following the cluster's app pattern (repository `k3s-gitops`, its `docs/app-nova.md`). Nothing here is applied yet; this is the plan and the order.

## Prerequisites on the platform

| Step in `k3s-gitops` | Why North needs it |
|---|---|
| Sealed Secrets (step 4) | `north-env` (database URLs) lives in Git, encrypted |
| Crossplane + provider-sql (step 5) | creates the `north` database and its roles from Git (record 0001/D3) |
| Postgres server backup with a restore test | required before curated data (pilot, curation) reaches production (NFR-16). The first load is official data only and can be rebuilt, so it does not block the first deploy |

## Pieces

| Piece | Where | Notes |
|---|---|---|
| Image | `ghcr.io/murilonegrao/north:sha-<7>` | built and pushed by `.github/workflows/imagem.yml` on pushes to `main` only |
| App manifests | `k3s-gitops/manifests/north/` | Deployment, Service, Ingress (`north.harpia.info`), headers middleware **without** `noindex` (record 0001/D5), `app.yaml` with `imagens: north=ghcr.io/murilonegrao/north` |
| Database | Crossplane `Banco` claim in the same folder | two roles: `north_owner` (owns the schema, migrations only) and `north_app` (DML only), like `deploy/postgres/init/10-roles.sql` locally |
| Secrets | `north-env` (sealed) | `NORTH_DATABASE_URL` (as `north_app`) for the app and loader; the migration URL (as `north_owner`) only in the migration initContainer |
| Migrations | initContainer `alembic upgrade head` with the owner URL | the app container never sees the owner URL |
| Health | `/api/health` | readiness and liveness probes (the path is `/api/health`, not `/health`) |
| First data load | Job `north-load-official-data` | template in [`deploy/k8s/load-official-data-job.yaml`](../deploy/k8s/load-official-data-job.yaml); files go into a PVC first |

## Order

1. Platform steps 4 and 5 are done.
2. Add `manifests/north/` to `k3s-gitops` with the database claim, the sealed `north-env`, the Deployment (with the migration initContainer), Service, Ingress and middleware. Push: the ApplicationSet creates the app, the Image Updater sets the tag, ArgoCD deploys.
3. Check `https://north.harpia.info/api/health`, then the security headers (`curl -sI`): the app sets CSP, `X-Frame-Options`, `nosniff`, `Referrer-Policy`, `Permissions-Policy`; Traefik adds HSTS.
4. Create the PVC `north-source-files`, copy the official files into it (layout in the Job file), run the Job once, and check the counts against a local load (132 Texas programs on the 2026-11 files).
5. Later, the upload screen (FR-26) replaces the manual copy into the PVC.

## Alternative for the first load

Restoring a `pg_dump` of a local database also works, but it ships the state of one machine instead of rebuilding from the sources; prefer the Job.

## Before production

See "Security before production" in the [execution plan](execution-plan.md): rate limiting at the ingress, image scan in CI, branch protection on `main`, GHCR package visibility, uploads in a worker with time limits.
