# BoxdMetrics

> Production-grade serverless analytics platform with automated pipeline. Processes Letterboxd movie data through a CI/CD pipeline to AWS Lambda, delivering sub-second personalized insights.

[![CI/CD](https://img.shields.io/github/actions/workflow/status/paulobarb/BoxdMetrics/backend.yml?label=CI%2FCD&style=flat-square)](https://github.com/paulobarb/BoxdMetrics/actions)
[![Infrastructure](https://img.shields.io/badge/Terraform-AWS%20Lambda-orange?style=flat-square&logo=terraform)](infra/terraform/)
[![Security](https://img.shields.io/badge/security-SLSA%20L1-green?style=flat-square)](.github/workflows/backend.yml)
[![License](https://img.shields.io/github/license/paulobarb/BoxdMetrics?style=flat-square)](LICENSE)

**Live Demo:** [boxd-metrics.vercel.app](https://boxd-metrics.vercel.app)  

---

## Executive Summary

BoxdMetrics workflow: developer commits code → automated security pipeline validates → infrastructure deploys as code. The architecture prioritizes **security-by-default**, **cost-efficiency** (scales to zero), and **zero-downtime deployments**.

Key achievements:
- **Security-gated CI/CD:** 5-layer security checks prevent vulnerable code from reaching production
- **Serverless-first:** AWS Lambda architecture costs ~$0.55/month vs $20+/month for always-on compute
- **Infrastructure as Code:** Complete AWS environment reproducible via Terraform
- **Zero-trust security:** CORS-locked origins, API key auth, least-privilege IAM

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────────┐
│                           GitHub Actions (CI/CD)                           │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │  Security   │───>│    Build    │───>│    Scan     │───>│   Deploy    │  │
│  │  Layer 1-5  │    │   + Test    │    │    Trivy    │    │  AWS ECR    │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS Cloud (Terraform)                          │
│                                                                             │
│   ┌──────────────────┐         ┌─────────────────────────────────────┐      │
│   │   ECR Registry   │         │         Lambda Function             │      │
│   │   ┌──────────┐   │         │   ┌─────────────────────────────┐   │      │
│   │   │ :latest  │───┼─────────┼──>│  FastAPI + Mangum Adapter   │   │      │
│   │   └──────────┘   │         │   │  • 30s timeout              │   │      │
│   └──────────────────┘         │   │  • 512MB RAM                │   │      │
│                                │   │  • Python 3.12              │   │      │
│                                │   └─────────────┬───────────────┘   │      │
│                                │                 │                   │      │
│                                │   ┌─────────────▼────────────┐      │      │
│    ┌──────────────────┐        │   │   Function URL (CORS)    │      │      │
│    │   Data Layer     │        │   │  ─────────────────────── │      │      │
│    │  ┌────────────┐  │        │   │  Origins: Vercel-locked  │      │      │
│    │  │ S3 (CSV)   │  │        │   │  Auth: App-level         │      │      │
│    │  │ DynamoDB   │  │        │   └──────────────────────────┘      │      │
│    │  └────────────┘  │        └─────────────────────────────────────┘      │
│    └──────────────────┘                                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼ HTTPS
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Vercel Edge (Frontend)                         │
│                                   React + Vite                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack & Security Layers

| Category | Technology | Security Purpose |
|----------|-----------|------------------|
| **Frontend** | React, Vite | CSP headers, build-time env injection |
| **Backend** | FastAPI, Python | Input validation, type safety, rate limiting |
| **Serverless** | AWS Lambda (Mangum) | No persistent attack surface, IAM-isolated |
| **Container** | Docker multi-stage | Minimal attack surface, distroless where possible |
| **Registry** | Amazon ECR | Image scanning on push, immutable tags |
| **CI/CD** | GitHub Actions | OIDC authentication (no long-lived secrets) |
| **SAST** | Bandit, Ruff | Python vulnerability detection |
| **Secrets** | Gitleaks | Pre-commit secret detection |
| **Dependencies** | pip-audit | CVE scanning for supply chain |
| **Images** | Trivy | OS + library vulnerability scanning |
| **IaC** | Terraform | Version-controlled infrastructure, plan reviews |
| **Auth** | AWS IAM + OIDC | Federated identity, no static credentials |
| **Monitoring** | CloudWatch + Prometheus | Observability, alerting |

---

## Infrastructure as Code

Two documented architectural iterations tracked in the `infra/` directory:

### [Current Architecture: Serverless Lambda (V2)](infra/terraform/)

```hcl
# resources: Lambda, ECR, S3, DynamoDB, IAM, CloudWatch
# cost: ~$0.55/month at current usage
# cold start: ~2-4 seconds
```

**Optimizations:**
- Function URL CORS strictly bound to Vercel origins
- Lambda memory tuned at 512MB (price/performance sweet spot)
- CloudWatch Logs 7-day retention (cost vs debugging tradeoff)

### [Legacy Architecture: ECS Fargate (V1)](infra/terraform-legacy/)

```hcl
# resources: ECS Cluster, Fargate Tasks, VPC
# cost: ~$20+/month (always-on)
# use case: Sustained load, custom networking requirements
```

Documented for reference showing evolution toward serverless-first design.

---

## Local Development

**Prerequisites:** Docker, Docker Compose, Node.js 22+

```bash
# Clone repository
git clone https://github.com/paulobarb/BoxdMetrics.git
cd BoxdMetrics

# Start frontend + backend + monitoring stack
docker-compose up --build -d
```
- RUN: http://localhost:5174

**Local Services:**
| Service | URL | Purpose |
|---------|-----|---------|
| API | http://localhost:8000 | FastAPI backend |
| API Docs | http://localhost:8000/docs | OpenAPI/Swagger UI |
| Prometheus | http://localhost:9090 | Metrics scraping |
| Grafana | http://localhost:3000 | Visualization (admin/admin) |

---

## Monitoring & Observability

### Production (AWS CloudWatch)

| Metric | Source | Alert Threshold (to-do)|
|--------|--------|-----------------|
| Invocations | Lambda | N/A (usage tracking) |
| Duration | Lambda | > 5s (p99 latency / Cold Start monitoring) |
| Errors | Lambda | > 1% error rate |

### Local Development (Prometheus + Grafana)

Two custom dashboards for development debugging:

**[AppHealth.json](infra/monitoring/grafana/AppHealth.json)** - RED Metrics
- Request rate, latency (p95), error rate
- Tracks what end-users experience

**[Infrastructure.json](infra/monitoring/grafana/Infrastructure.json)** - USE Metrics
- CPU, memory, container restarts
- Detects resource exhaustion and memory leaks

See [infra/monitoring/README.md](infra/monitoring/) for detailed dashboard documentation.

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  THREAT MODEL                                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Threat: Unauthorized API Access                                            │
│  Mitigation: X-API-Key header validation (FastAPI dependency)               │
│                                                                             │
│  Threat: Credential Leakage (Git commit)                                    │
│  Mitigation: Zero-config 'dummy' keys for local dev + GitHub Secrets        │
│                                                                             │
│  Threat: Dependency Supply Chain Attack                                     │
│  Mitigation: pip-audit CVE scanning + lock files                            │
│                                                                             │
│  Threat: Container Escape                                                   │
│  Mitigation: Distroless images + Trivy scanning + minimal privileges        │
│                                                                             │
│  Threat: DDoS / Billing Attack                                              │
│  Mitigation: CORS origin blocking + rate limiting (slowapi + Redis)         │
│                                                                             │
│  Threat: Injection (CSV parsing)                                            │
│  Mitigation: Pandas strict column validation, size limits (2MB max)         │
│                                                                             │
│  Threat: IAM Privilege Escalation                                           │
│  Mitigation: Least-privilege roles, OIDC conditions (repo/branch match)     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Testing Strategy

```bash
# Unit tests (pytest)
cd src/backend
pytest tests/ -v

# Security scan (Bandit)
bandit -r . -x tests/

# Dependency audit
pip-audit -r requirements.txt

# Local security check
docker run --rm -v $(pwd):/code aquasec/trivy fs /code
```

---

## Project Structure

```
BoxdMetrics/
├── src/
│   ├── backend/
│   │   ├── api/routes.py          # FastAPI endpoints
│   │   ├── core/
│   │   │   ├── security.py         # Auth, rate limiting
│   │   │   └── config.py           # Environment config
│   │   ├── services/
│   │   │   └── etl_letterboxd.py   # CSV processing logic
│   │   ├── main.py                 # Lambda handler entry
│   │   ├── Dockerfile              # Local development
│   │   ├── Dockerfile.aws          # Production Lambda image
│   │   └── tests/
│   │       ├── test_routes.py      # API integration tests
│   │       └── test_etl.py         # ETL unit tests
│   └── frontend/
│       ├── src/App.jsx             # React components
│       └── Dockerfile
├── infra/
│   ├── terraform/                  # Current Lambda infrastructure
│   ├── terraform-legacy/           # Documented ECS evolution
│   └── monitoring/                 
│       ├── prometheus.yml          # Scrape configurations
│       └── grafana/                # Provisioning & JSON Dashboards
├── .github/workflows/
│   └── backend.yml                 # CI/CD pipeline
├── docker-compose.yaml             # Local orchestration
└── README.md
```

---

## Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| Cold Start | 1-2s | Python + Pandas initialization |
| Warm Response | <200ms | Cached Lambda execution |
| Max File Size | 2MB | CSV upload limit |
| Rate Limit | 3 req/min per IP | Configurable via slowapi |
| Monthly Cost | ~$0.55 | Lambda free tier covers usage |

---

## License

MIT - See [LICENSE](LICENSE)

---

## Contact

Built by [Paulo Barbosa](https://github.com/paulobarb)
