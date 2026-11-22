# Admin area and worker on k3s (record 0006)

Files to copy into `k3s-gitops/manifests/north/` and list in its `kustomization.yaml`. The image
tag comes from the same `images:` entry as the web Deployment, so the worker always runs the
same version.

| File | What |
|---|---|
| `raw-pvc.yaml` | PVC `north-raw`: raw official files and the upload inbox |
| `worker.yaml` | Deployment `north-worker` (`python -m north.jobs.worker`), the only pod that downloads |
| `web-patch.yaml` | what changes in the existing `north` Deployment: the upload inbox, the client IP header |
| `networkpolicy-egress.yaml` | only the worker reaches the internet (https, and SMTP on 465); the web pod reaches Postgres and DNS |
| `api-keys.secret.example.yaml` | shape of the `north-api-keys` Secret, to seal with kubeseal (never commit it filled) |
| `smtp.secret.example.yaml` | shape of the `north-smtp` Secret: the SMTP login of the sending mailbox (record 0007) |

Email (record 0007): the web process only queues messages in `email_outbox`; the worker sends
them. Deliverability needs the sending domain's SPF, DKIM and DMARC records at the DNS provider.

The step-by-step order is in the private runbook the author keeps outside the repository.
