# Phase 18 — Deployment, Scaling & Observability

**Goal:** Run the whole system reliably in production: containerized services, a job/queue
architecture that scales the GPU-heavy generator independently, object storage, autoscaling,
monitoring, cost controls, and CI/CD.

**Depends on:** All service phases (esp. 03, 08). Best done incrementally alongside them.

---

## Tasks

1. **Containerization & orchestration**
   - Production Dockerfiles (multi-stage, slim) for each service. Kubernetes manifests/Helm (or a
     PaaS: Render/Fly/AWS ECS+Fargate). Separate deployments per service for independent scaling.
   - Config/secrets via env + a secrets manager (SSM/Sealed Secrets/Vault).

2. **Data & storage**
   - Managed Postgres (+PostGIS) with backups/PITR; Redis (managed) for cache+queue; S3 (managed)
     for artifacts with lifecycle rules; Qdrant managed or self-hosted with persistence.
   - Migrations run as a pre-deploy job (Alembic).

3. **Worker & GPU scaling**
   - CPU worker pool (solver, validation, geometry, export) and a **separate GPU worker pool** for
     the ML generator, autoscaled on queue depth (KEDA / queue-length metric). Scale GPU to zero
     when idle to control cost. Job timeouts, retries, dead-letter queue.

4. **API scaling & realtime**
   - Stateless API behind a load balancer; horizontal autoscale on CPU/RPS. WebSocket support via
     sticky sessions or a pub/sub (Redis) fan-out so progress reaches the right client across pods.

5. **CDN & assets**
   - Serve glTF/IFC/DWG artifacts and the web app via CDN; signed URLs for private artifacts;
     compression (Draco for glTF, gzip/brotli for text). Cache busting on deploy.

6. **CI/CD**
   - Build/test/scan on PR; build+push images on merge; deploy to staging automatically, prod on
     approval. Blue/green or canary. DB migration safety gates. Rollback runbook.

7. **Observability & cost**
   - OpenTelemetry traces end-to-end (api→worker→service), Prometheus/Grafana dashboards (queue
     depth, job latency, GPU utilization, error rates), structured logs (Loki), Sentry for errors.
   - **Cost guardrails**: GPU autoscale-to-zero, per-org generation quotas/rate limits, budget alerts.
   - SLOs (generation p95, API p99, uptime) + alerting.

8. **Environments**
   - dev (compose) / staging / prod parity; seeded demo data in staging; feature flags for the ML
     path and experimental features.

---

## Deliverables

- Reproducible prod deployment of all services with managed datastores and object storage.
- Independent CPU + GPU autoscaling driven by queue depth; GPU scales to zero when idle.
- CI/CD with staging→prod promotion, migrations, and rollback.
- Dashboards, tracing, error tracking, SLOs, and cost guardrails.

## Acceptance criteria

- A load test of concurrent generations scales GPU workers up and back to zero afterward.
- A failed job lands in the DLQ and is retryable; API stays responsive under generator load.
- WebSocket progress reaches the correct client across multiple API pods.
- A bad deploy can be rolled back via a documented runbook; migrations are gated and reversible.
- Dashboards show per-job latency and GPU utilization; a budget alert fires in a forced test.

## Sources

- Kubernetes: https://kubernetes.io/ · Helm: https://helm.sh/ · KEDA (queue autoscaling): https://keda.sh/
- OpenTelemetry: https://opentelemetry.io/ · Prometheus/Grafana: https://grafana.com/
- Arq workers: https://arq-docs.helpmanual.io/ · Sentry: https://sentry.io/
- glTF Draco / CDN delivery: https://google.github.io/draco/

---

## Claude build prompt

> Implement Phase 18 (Deployment, Scaling & Observability) per `plan/phase-18-deploy-scale.md`.
> Create multi-stage production Dockerfiles for every service and Kubernetes/Helm manifests (or a
> documented PaaS equivalent) with per-service deployments, env-based config, and a secrets manager.
> Provision managed Postgres+PostGIS (backups/PITR), Redis (cache+queue), S3 artifacts (lifecycle +
> signed URLs), and Qdrant with persistence; run Alembic migrations as a gated pre-deploy job.
> Configure a CPU worker pool and a SEPARATE GPU worker pool for the ML generator, autoscaled on
> queue depth via KEDA and scaling GPU to zero when idle, with job timeouts, retries, and a
> dead-letter queue. Make the API stateless behind a load balancer with HPA, and support WebSocket
> progress across pods via Redis pub/sub. Serve artifacts and the web app via CDN with Draco/brotli
> compression and cache busting. Build CI/CD that tests+scans on PR, builds/pushes images on merge,
> auto-deploys to staging and prod-on-approval with blue/green or canary and a rollback runbook. Add
> end-to-end OpenTelemetry tracing, Prometheus/Grafana dashboards (queue depth, job latency, GPU
> utilization, error rates), structured logs, Sentry, SLOs/alerting, and cost guardrails (GPU
> scale-to-zero, per-org generation quotas/rate limits, budget alerts). Acceptance: a concurrent-
> generation load test scales GPU up then back to zero, failed jobs hit a retryable DLQ while the API
> stays responsive, WebSocket progress reaches the right client across pods, a bad deploy rolls back
> via the runbook, and dashboards plus a forced budget alert work.
