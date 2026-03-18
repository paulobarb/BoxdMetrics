# 📦 BoxdMetrics

> A data analytics API built on a DevSecOps foundation — containerized, automatically scanned, and monitored with Prometheus and Grafana.

![CI/CD](https://img.shields.io/github/actions/workflow/status/paulobarb/BoxdMetrics/ci.yml?label=CI%2FCD&style=flat-square)
![License](https://img.shields.io/github/license/paulobarb/BoxdMetrics?style=flat-square)

---

## What is this?

BoxdMetrics processes your [Letterboxd](https://letterboxd.com) export data through a FastAPI backend, exposing a REST API with cached analytics. The app itself is simple, the engineering around it is the point.

This project was built to demonstrate a real DevSecOps workflow: security checks are not an afterthought but gated directly into the CI pipeline, and infrastructure is managed as code.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          GitHub Actions                              │
│   security → build (test + push to GHCR) → scan (trivy) → deploy*  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────┐
│              Local / AWS* (Terraform*)               │
│                                                      │
│   ┌─────────────┐        ┌──────────────────────┐   │
│   │   FastAPI    │◄──────│   CSV / S3*          │   │
│   │  (Docker)    │       └──────────────────────┘   │
│   └──────┬──────┘                                   │
│          │                                           │
│   ┌──────▼──────┐                                   │
│   │    Redis     │                                   │
│   └─────────────┘                                   │
└─────────────────────────────────────────────────────┘
                             │
                             ▼ /metrics
┌─────────────────────────────────────────────────────┐
│                    Monitoring                        │
│              Prometheus + Grafana                    │
│         (RED metrics + USE metrics dashboards)       │
└─────────────────────────────────────────────────────┘
```

> `*` — Planned: AWS ECS Fargate deployment, S3 storage, Terraform provisioning, deploy pipeline job.

---

## Tech Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Containers** | Docker + Compose | Local orchestration & image builds |
| **CI/CD** | GitHub Actions | Automated pipeline (security → build → scan) |
| **SAST** | Bandit | Static analysis on Python source |
| **Secret Detection** | Gitleaks | Prevents hardcoded credentials from merging |
| **Dependency Audit** | pip-audit | CVE scanning on Python dependencies |
| **Image Scanning** | Trivy | CVE scanning on production Docker image |
| **Backend** | FastAPI + Pandas | REST API and CSV ETL |
| **Caching** | Redis | Response caching for analytics endpoints |
| **Monitoring** | Prometheus + Grafana | Metrics scraping via `/metrics` endpoint |
| **Cloud (planned)** | AWS ECS Fargate + S3 | Serverless container hosting |
| **IaC (planned)** | Terraform | Reproducible infrastructure provisioning |

---

## CI/CD Pipeline

Every push to `main` runs 3 jobs in sequence. A failure at any stage blocks the merge.

```
job: security
  ├── gitleaks       — secret detection across full git history
  ├── ruff           — Python linting
  ├── bandit         — Python SAST
  └── pip-audit      — dependency CVE audit

job: build            (requires security to pass)
  ├── pytest         — automated tests
  └── docker build   — image built and pushed to GHCR

job: scan             (requires build to pass)
  └── trivy          — CVE scan on image (fails on HIGH/CRITICAL)

job: deploy           (planned — requires scan to pass)
  └── push to AWS ECS Fargate
```

---

## Security Decisions

**Shift-left approach:** security tools run before the Docker build step. A vulnerable dependency or hardcoded secret never makes it into an image.

**Trivy configuration:** the pipeline fails on `HIGH` and `CRITICAL` CVEs only. `MEDIUM` and below are logged but non-blocking, a deliberate tradeoff to avoid alert fatigue on base image noise.

**GHCR:** Docker images are pushed to GitHub Container Registry using `GITHUB_TOKEN`, no external registry credentials needed.

**Planned:** AWS credentials injected via GitHub Actions OIDC, no long-lived keys stored as secrets.

---

## Monitoring

BoxdMetrics exposes a `/metrics` endpoint in Prometheus format via `prometheus-fastapi-instrumentator`.

Two Grafana dashboards are included:

**App Health (RED metrics)**
- Request rate on `/upload/`
- 95th percentile latency
- Average processing time
- Error rate percentage

**Infrastructure (USE metrics)**
- Memory usage (deriv — detects leaks)
- CPU usage
- Container crash detection
- Open file descriptors

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'boxdmetrics-api'
    static_configs:
      - targets: ['backend:8000']
```

---

## Project Structure

```
BoxdMetrics/
├── src/
│   ├── backend/
│   │   ├── main.py               # FastAPI app + /metrics endpoint
│   │   ├── etl.py                # Pandas CSV processing
│   │   ├── requirements.txt      # Production dependencies
│   │   ├── requirements-dev.txt  # CI/dev tools
│   │   ├── Dockerfile
│   │   └── tests/
│   │       └── test_etl.py       # pytest test suite
│   └── frontend/                 # React UI
├── infra/
│   ├── monitoring/
│   │   └── prometheus.yml
│   └── terraform/                # planned
├── .github/
│   └── workflows/
│       └── ci.yml                # CI pipeline
├── docker-compose.yml
└── README.md
```

---

## Quick Start (Local)

**Prerequisites:** Docker & Docker Compose, your Letterboxd export files

```bash
git clone https://github.com/paulobarb/BoxdMetrics.git
cd BoxdMetrics

# Start the stack
docker-compose up --build
```

- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Metrics: `http://localhost:8000/metrics`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`

---

## Data Privacy

Personal Letterboxd CSV files are explicitly excluded via `.gitignore` and never committed to the repository.
