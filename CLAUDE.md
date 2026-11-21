# BoxdMetrics

Upload a Letterboxd CSV export, get viewing stats. Portfolio project for junior DevOps / Cloud / Platform roles, so **the docs must match the code**: never claim something in a README that the code doesn't do.

## Session workflow

- **Start of session:** read `docs/PROGRESS.md` before doing anything else.
- **End of session (or when I say "wrap up" / run `/wrap-up`):** update `docs/PROGRESS.md`: what was done, decisions taken and why, what's next. Keep it short, newest entry first.

## Stack

- **Backend:** FastAPI + Pandas (`src/backend`), runs on AWS Lambda via Mangum (`main.handler`). Rate limiting with slowapi (Redis locally, in-memory on Lambda).
- **Frontend:** React 19 + Vite (`src/frontend`), deployed on Vercel. The `VITE_API_KEY` ships in the bundle, so treat it as public.
- **Infra:** Terraform in `infra/terraform` (Lambda, ECR, IAM, CloudWatch, S3, DynamoDB), region `eu-north-1`. `infra/terraform-legacy` is the old ECS Fargate version, for reference only. Don't change it.
- **CI/CD:** `.github/workflows/backend.yml`: Ruff, Bandit, pip-audit and Gitleaks, then pytest, a Docker build (`Dockerfile.aws`) and Trivy, then a push to ECR and a Lambda update (on push to `main` only). AWS auth is OIDC only, with no access keys.
- **Local monitoring:** Prometheus + Grafana via Docker Compose (`infra/monitoring`).

## Commands

Run from the repo root unless noted.

```bash
# Full local stack (frontend :5174, API :8000, Prometheus :9090, Grafana :3000)
docker-compose up --build -d

# Backend tests (same as CI)
PYTHONPATH=./src/backend python -m pytest ./src/backend/tests

# Lint and security checks (same as CI). Use ruff 0.15.6: newer versions flag extra rules
ruff check src/backend
bandit -r src/backend -x src/backend/tests
pip-audit -r src/backend/requirements.txt -r src/backend/requirements-dev.txt --ignore-vuln CVE-2026-4539

# Frontend
cd src/frontend && npm run lint && npm run build

# Terraform (read-only checks are fine; see the rules below for anything else)
cd infra/terraform && terraform fmt -check && terraform validate
```

## Rules

- **Git:** never commit or push to `main`. Work on a branch (`feat/...`, `fix/...`, `docs/...`) and open a PR. Small commits with clear messages.
- **Verify before saying "done":** run the tests and the relevant linters, and show the result. If something can't be run, say so.
- **Terraform:** never run `terraform apply` or `destroy`, or touch state. `plan` only, and only if I ask. The AWS budget is tight (free credits), so flag any change that adds cost.
- **Secrets:** never write real keys, tokens or ARNs with account IDs into files. `dev_secret_123` is a local-dev placeholder only. Secrets go in GitHub Secrets or `terraform.tfvars` (gitignored).
- **Dependencies:** add runtime deps to `requirements.txt` **and** regenerate `requirements-lock.txt` (the Docker images install from the lock file).
- **Docs:** when behaviour changes, update the matching README (root, `infra/terraform`, `infra/monitoring`) and the "Known gaps" list in the same PR.
- **Explain, don't just do:** I'm learning. For non-obvious changes, explain the why in a sentence or two so I can defend it in an interview.

## Gotchas

- Imports in the backend are relative to `src/backend` (`from core.security import ...`), so `PYTHONPATH` must point there.
- `main.py` only adds CORS and the Prometheus `/metrics` endpoint outside Lambda (checks `LAMBDA_TASK_ROOT`). Production CORS is set on the Lambda Function URL in Terraform.
- Tests set `REDIS_URL=memory://` in `conftest.py`, so no Redis is needed to run them.
- `.court/` and `static_analysis_semgrep_*/` are local review/scan output and are gitignored.
