# Deploy, Scale & Observe (Phase 18)

Production deployment of the Studio. Dev uses `infra/docker-compose.yml`; prod uses these
Kubernetes manifests (or a PaaS equivalent — Render/Fly/ECS — the shape is the same).

## Topology
- **api** (stateless, HPA on CPU/RPS) behind an ingress/LB.
- **worker** (Arq) — CPU pool; **autoscaled on Redis queue depth via KEDA, scale-to-zero** when idle.
  The ML generator pool (Phase 08 ML path) is a separate GPU deployment with the same KEDA pattern.
- **web** (static SPA) served via CDN/ingress.
- Domain services (validator/geometry/export/codes/generator) — one Deployment + Service each
  (only `api`/`worker`/`web` are templated here; the rest follow the identical pattern).
- Managed datastores (not in-cluster for prod): Postgres+PostGIS, Redis, S3, Qdrant.

## Apply
```bash
kubectl create namespace fpg
kubectl -n fpg apply -f infra/k8s/manifests.yaml
kubectl -n fpg apply -f infra/k8s/keda-scaledobject.yaml   # needs KEDA installed
```
Images are placeholders (`ghcr.io/OWNER/fpg-*`); substitute via Kustomize/Helm overlays per env.
Secrets come from a real secrets manager (SealedSecrets/SSM/Vault) — `fpg-secrets` here is a stub.

## Observe
- Every service exposes Prometheus metrics at `/metrics`; scrape config in
  `infra/observability/prometheus.yml`. Add Grafana dashboards for queue depth, job latency, GPU
  utilization, error rate; OpenTelemetry traces span api→worker→service.
- SLOs: generation p95, API p99, uptime. Alert on queue backlog + budget.

## Cost guardrails
- GPU generator scales to **zero** when idle (KEDA). Per-org generation/export **quotas + rate
  limits** at the api. Budget alerts on cloud spend. S3 lifecycle rules on artifacts.
