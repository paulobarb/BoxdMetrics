# Terraform: Serverless Lambda Architecture (V2)

> **Status:** Production  
> **Estimated Cost:** ~$0.55/month (~100 requests/day)  
> **Architecture:** Serverless-first (scales to zero)

---

## Philosophy

This architecture prioritizes **cost-efficiency** and **operational simplicity** over always-on availability. For an API with hours or days between requests, paying by millisecond is significantly cheaper than 24/7 infrastructure.

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Lambda over ECS | 99% cost reduction for low-traffic workload |
| Function URLs over API Gateway | No additional cost, simpler CORS |
| Container images over ZIP | Portability, dependency management |
| OIDC over access keys | No long-lived credentials in CI/CD |
| On-demand DynamoDB | Pay per request, not provisioned |
| Terraform over SAM/CDK | Explicit resource control, state locking |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS Cloud (eu-north-1)                         │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                         IAM & Security                              │   │
│   │  ┌─────────────────────┐      ┌─────────────────────────────────┐   │   │
│   │  │  GitHub OIDC        │      │  Lambda Execution Role          │   │   │
│   │  │  (Federated Trust)  │─────▶│  • CloudWatch Logs              │   │   │
│   │  │  repo:BoxdMetrics:* │      │  • S3 Put/Get                   │   │   │
│   │  └─────────────────────┘      │  • DynamoDB Write/Read          │   │   │
│   │         │                     └─────────────────────────────────┘   │   │
│   │         │  No AWS credentials in GitHub                             │   │
│   │         ▼                                                           │   │
│   │ ┌─────────────────────────────────────────────────────────────────┐ │   │
│   │ │GitHub Actions can assume role via sts:AssumeRoleWithWebIdentity │ │   │
│   │ └─────────────────────────────────────────────────────────────────┘ │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                         Compute Layer                               │   │
│   │                                                                     │   │
│   │  ┌──────────────────┐          ┌────────────────────────────┐       │   │
│   │  │  ECR Registry    │          │     Lambda Function        │       │   │
│   │  │  ─────────────   │          │  ┌─────────────────────┐   │       │   │
│   │  │  boxdmetrics     │─────────▶│  │ Container Image     │   │       │   │
│   │  │  -api-production │   Push   │  │ ┌───────────────┐   │   │       │   │
│   │  │  ┌─────────┐     │          │  │ │ Python 3.12   │   │   │       │   │
│   │  │  │ :latest │◀────┼──────────│  │ │ FastAPI       │   │   │       │   │
│   │  │  │ :sha    │     │  Image   │  │ │ Mangum        │   │   │       │   │
│   │  │  └─────────┘     │          │  │ └───────────────┘   │   │       │   │
│   │  └──────────────────┘          │  └─────────────────────┘   │       │   │
│   │                                │            │               │       │   │
│   │                                │            ▼               │       │   │
│   │                                │      ┌─────────────┐       │       │   │
│   │                                │      │ 30s timeout │       │       │   │
│   │                                │      │  512MB RAM  │       │       │   │
│   │                                │      └─────────────┘       │       │   │
│   │                                └────────────────────────────┘       │   │
│   │                                                                     │   │
│   │                      ┌─────────────────────────────┐                │   │
│   │                      │         Function URL        │                │   │
│   │                      │  ─────────────────────────  │                │   │
│   │                      │  https://xxx.lambda-url...  │                │   │
│   │                      │  Authorization: NONE        │                │   │
│   │                      │  CORS: Vercel-locked        │                │   │
│   │                      └─────────────────────────────┘                │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                              Data Layer                             │   │
│   │                                                                     │   │
│   │   ┌───────────────────────┐           ┌─────────────────────────┐   │   │
│   │   │  S3 Bucket            │           │  DynamoDB Table         │   │   │
│   │   │  ──────────────       │           │  ─────────────────      │   │   │
│   │   │  boxdmetrics-csv      │           │  boxdmetrics-stats      │   │   │
│   │   │  uploads              │           │  ─────────────────      │   │   │
│   │   │  • Encrypted (AES256) │           │  • UserId (PK)          │   │   │
│   │   │  • Versioning         │           │  • On-demand billing    │   │   │
│   │   └───────────────────────┘           │  • TTL for cleanup      │   │   │
│   │                                       └─────────────────────────┘   │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                             Observability                           │   │
│   │                                                                     │   │
│   │              /aws/lambda/boxdmetrics-api-production                 │   │
│   │                └── 7-day log retention                              │   │
│   │                                                                     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Resources Defined

### Compute

| Resource | Purpose | Configuration |
|----------|---------|---------------|
| `aws_ecr_repository.api` | Docker image storage | AES256 encryption, scan-on-push |
| `aws_lambda_function.api` | Serverless compute | 512MB RAM, 30s timeout, container |
| `aws_lambda_function_url.api_url` | HTTPS endpoint | CORS-restricted origins |

### Data Storage

| Resource | Purpose | Configuration |
|----------|---------|---------------|
| `aws_s3_bucket.csv_uploads` | Raw CSV storage | Encrypted, versioned |
| `aws_dynamodb_table.user_movie_stats` | Cached analytics | On-demand billing, string PK |
| `aws_cloudwatch_log_group.api` | Execution logs | 7-day retention |

### IAM & Security

| Resource | Purpose | Configuration |
|----------|---------|---------------|
| `aws_iam_openid_connect_provider.github` | GitHub Actions trust | OIDC federation |
| `aws_iam_role.github_actions` | CI/CD deployment | Scoped to this repo |
| `aws_iam_role_policy.github_actions_policy` | Deployment permissions | ECR + Lambda only |
| `aws_iam_role.lambda_execution_role` | Lambda runtime | CloudWatch, S3, DynamoDB |
| `aws_iam_policy.lambda_app_permissions` | App-specific access | Least-privilege |

### Terraform Backend

| Resource | Purpose | Configuration |
|----------|---------|---------------|
| `aws_s3_bucket.terraform_state` | State persistence | Versioned, encrypted |
| `random_id.suffix` | Unique bucket names | 4 bytes entropy |

---

## Cost Breakdown (Monthly)

| Service | Estimate | Notes |
|---------|----------|-------|
| **Lambda** | $0.02 | Free tier covers usage |
| **CloudWatch Logs** | $0.50 | 7-day retention, minimal |
| **DynamoDB** | $0.00 | On-demand, low volume |
| **S3** | $0.01 | < 1GB storage, low requests |
| **ECR** | $0.00 | Single small image, free tier |
| **Data Transfer** | $0.02 | Outbound via Function URL |
| **Total** | **~$0.55** | Scales with usage |

*Cost model assumes ~100 requests/day, average 200ms execution.*

**Cost Control Safeguards:**
- Reserved concurrency limits (throttling protection)
- CloudWatch retention limits (log cost control)
- S3 lifecycle policies (auto-cleanup consideration)

---

## Deployment Flow

```
GitHub Push
│
├─ Security Scan
│  ├── Gitleaks ──▶ secrets detection
│  ├── Ruff ──────▶ linting
│  ├── Bandit ────▶ Python SAST
│  └── pip-audit ─▶ dependency CVEs
│
├─ Build & Scan
│  ├── pytest ────▶ etl tests
│  ├── docker build
│  └── trivy ─────▶ image CVE scan
│      └── (fails on HIGH/CRITICAL)
│
└─ Deploy
   ├── docker push ───────────────────┐
   │   ├── ECR tag: <sha>             │
   │   └── ECR tag: latest            │
   │                                  ▼
   └── aws lambda update-function-code
       └── boxdmetrics-api-production
```

**Deployment guarantees:**
- Tagged images enable instant rollback
- State locking prevents concurrent modifications
- OIDC authentication (no credentials in repo)
- All security gates must pass

---

## Security Model

### Layer 1: Lambda Function URL (Edge)

```hcl
# CORS strictly locked to approved origins
resource "aws_lambda_function_url" "api_url" {
  authorization_type = "NONE"  # App-level auth, not AWS SigV4

  cors {
    allow_origins = [
      "http://localhost:5174",              # Local dev
      "http://localhost:3001",              # Alt local
      "https://boxd-metrics.vercel.app"     # Production
    ]
    allow_methods = ["POST"]
    allow_headers = ["*"]
    allow_credentials = true
    max_age = 86400
  }
}
```

**Denial Logic:** Non-whitelisted origins get CORS errors, requests never reach Lambda.

### Layer 2: Application (FastAPI)

```python
# Header-based API key validation
async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401)

# Rate limiting per IP
@limiter.limit("3/minute")
```

### Layer 3: IAM (Least Privilege)

| Role | Allowed Actions | Resource |
|------|-----------------|----------|
| `lambda_execution` | `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` | CloudWatch only |
| `lambda_app` | `s3:PutObject`, `s3:GetObject` | Specific bucket only |
| `lambda_app` | `dynamodb:PutItem`, `dynamodb:GetItem` | Specific table only |

### Layer 4: Infrastructure Hardening

```hcl
# ECR encryption
encryption_configuration {
  encryption_type = "AES256"
}

# Auto-vulnerability scanning
image_scanning_configuration {
  scan_on_push = true
}

# Secrets marked sensitive
variable "api_secret_key" {
  sensitive = true
}
```

---

## Files

| File | Purpose | Key Resources |
|------|---------|---------------|
| `main.tf` | Core infrastructure | Lambda, ECR, S3, DynamoDB, IAM roles |
| `oidc.tf` | GitHub Actions trust | OIDC provider, IAM assume policy |
| `providers.tf` | AWS configuration | eu-north-1, provider versions |
| `variables.tf` | Inputs | Environment, memory, secrets |
| `outputs.tf` | Useful references | Function URL, ECR repo, resources |
| `terraform.tfvars` | **Local only** - actual values |

---

## Security Considerations

### API Key Security

The `api_secret_key` is:
- Marked `sensitive = true` in Terraform (hidden in logs)
- Passed via Lambda environment variables
- Gateway key validation before processing

**Never:**
- Log the API key
- Return it in error messages
- Store it in client-side code

### CORS Configuration

Strict origin whitelist prevents:
- CSRF attacks from malicious sites
- Credential exposure
- Billing attacks (DDoS via unauthorized origins)

### IAM Boundaries

```hcl
# GitHub Actions can ONLY:
- ECR: Push, pull, describe repositories
- Lambda: Update function code, get function

Cannot:
- Delete resources
- Modify IAM
- Access other AWS accounts
- Elevate privileges
```

---

## When NOT To Use This

Lambda is NOT suitable when:

❌ **Sustained high throughput** (>100 req/s sustained)
❌ **Long-running processes** (>30s standard, >15min w/ streaming)
❌ **Microsecond latency requirements** (cold start: 1-2s)
❌ **Persistent connections** (WebSockets - use API Gateway + Lambda)
❌ **Stateful sessions** (must externalize to DB/cache)

---

## Related Documentation

- [Monitoring: Prometheus + Grafana](../monitoring/) - Local dev observability
- [Legacy: ECS Architecture](../terraform-legacy/) - Evolution rationale
- [Main README](../../README.md) - Project overview
