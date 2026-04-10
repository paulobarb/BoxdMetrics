# 📦 BoxdMetrics

> A full-stack data analytics application. Containerized, automatically scanned, deployed serverless, and managed via Infrastructure as Code.

![CI/CD](https://img.shields.io/github/actions/workflow/status/paulobarb/BoxdMetrics/backend.yml?label=CI%2FCD&style=flat-square)
![License](https://img.shields.io/github/license/paulobarb/BoxdMetrics?style=flat-square)

**Live Demo:** [boxd-metrics.vercel.app](https://boxd-metrics.vercel.app)

---

## What is this?

BoxdMetrics processes your [Letterboxd](https://letterboxd.com) export data through a Serverless FastAPI backend, returning cached, personalized movie analytics to a React frontend.

This project was built to demonstrate a real DevSecOps workflow: security checks are gated directly into the CI pipeline, compute is optimized for zero-idle cost via AWS Lambda, and infrastructure is strictly managed as code via Terraform.

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────────────┐
│                          GitHub Actions                             │
│   security → build (test + push to ECR) → scan (trivy) → deploy     │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────┐
│                AWS Cloud (Terraform)                │
│                                                     │
│   ┌─────────────┐        ┌──────────────────────┐   │
│   │ AWS Lambda  │◄───────│ S3 Bucket / DynamoDB │   │
│   │ (FastAPI)   │        └──────────────────────┘   │
│   └──────┬──────┘                                   │
│          ▲                                          │
└──────────┼──────────────────────────────────────────┘
           │ HTTPS / Function URL (CORS Locked)
           │
┌──────────▼──────────────────────────────────────────┐
│                      Frontend                       │
│            React + Vite (Hosted on Vercel)          │
└─────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | React, Vite, CSS | Client-side UI and file processing (Deployed on Vercel) |
| **Backend** | Python, FastAPI, Mangum | REST API and CSV ETL adapter for Lambda |
| **Containers** | Docker | Multi-stage optimized builds for AWS ECR |
| **CI/CD** | GitHub Actions | Automated pipeline (security → build → scan) |
| **SAST** | Bandit | Static analysis on Python source |
| **Secret Detection** | Gitleaks | Prevents hardcoded credentials from merging |
| **Dependency Audit** | pip-audit | CVE scanning on Python dependencies |
| **Image Scanning** | Trivy | CVE scanning on production Docker image |
| **Cloud** | AWS Lambda | Serverless compute (scales to zero) |
| **IaC** | Terraform | Reproducible infrastructure, IAM roles, and CORS provisioning |
| **Monitoring** | CloudWatch & Prometheus | Cloud execution logs & Local development metrics |


---

## CI/CD Pipeline

Every push to `main` runs jobs in sequence. A failure at any stage blocks the merge.

```text
job: security
  ├── gitleaks       — secret detection across full git history
  ├── ruff           — Python linting
  ├── bandit         — Python SAST
  └── pip-audit      — dependency CVE audit

job: build           (requires security to pass)
  ├── pytest         — automated tests
  └── docker build   — optimized multi-stage image built for AWS base

job: scan            (requires build to pass)
  └── trivy          — CVE scan on image (fails on HIGH/CRITICAL)

job: deploy          (requires scan to pass)
  └── AWS ECR        — pushes verified image to AWS registry
```

---

## Security Decisions

**Shift-left approach:** Security tools run before the Docker build step. A vulnerable dependency or hardcoded secret never makes it into an image.

**Trivy configuration:** The pipeline fails on `HIGH` and `CRITICAL` CVEs only. `MEDIUM` and below are logged but non-blocking, a deliberate tradeoff to avoid alert fatigue on base image noise.

**Strict CORS Architecture:** The AWS Lambda Function URL is protected via Terraform IAM and CORS policies. `allow_origins` is strictly bound to the Vercel production domain and local development, dropping unauthorized requests before Lambda execution to prevent billing attacks.

---

## Monitoring & Telemetry

Due to the ephemeral nature of AWS Lambda, production logs and OOM (Out of Memory) tracking are handled natively by **AWS CloudWatch**. 

For local development and load testing, BoxdMetrics exposes a `/metrics` endpoint in Prometheus format via `prometheus-fastapi-instrumentator` for container health monitoring.

**Local Infrastructure (USE metrics)**
* Memory usage (deriv — detects leaks in Pandas processing)
* CPU usage
* Container crash detection
* Open file descriptors

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'boxdmetrics-api'
    static_configs:
      - targets: ['backend:8000']
```

---

## Project Structure

```text
BoxdMetrics/
├── src/
│   ├── backend/
│   │   ├── main.py               # FastAPI app + Mangum Lambda adapter
│   │   ├── etl.py                # Pandas CSV processing
│   │   ├── requirements.txt      # Production dependencies
│   │   ├── Dockerfile            # Multi-stage AWS Lambda image
│   │   └── tests/
│   │       └── test_etl.py       # pytest test suite
│   └── frontend/                 # React Vite UI
├── infra/
│   └── terraform/                # AWS IaC (Lambda, ECR, IAM, S3)
├── .github/
│   └── workflows/
│       └── ci.yml                # CI/CD and Security pipeline
├── docker-compose.yml            # Local development orchestration
└── README.md
```

---

## Quick Start (Local Development)

**Prerequisites:** Docker & Docker Compose, Node.js, your Letterboxd export files.

### 1. Backend API
```bash
git clone [https://github.com/paulobarb/BoxdMetrics.git](https://github.com/paulobarb/BoxdMetrics.git)
cd BoxdMetrics

# Start the local backend simulation
docker-compose up --build
```
* API: `http://localhost:8000`
* API docs: `http://localhost:8000/docs`

### 2. Frontend UI
```bash
cd src/frontend
npm install

# Create local environment variable
echo "VITE_API_URL=http://localhost:8000/api/upload/" > .env

# Start React dev server
npm run dev
```
* UI: `http://localhost:5173`

---

## Data Privacy

Personal Letterboxd CSV files are explicitly excluded via `.gitignore` and never committed to the repository. The production AWS Lambda environment processes CSVs in RAM during execution and natively purges the data upon container shutdown.