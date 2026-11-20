# Terraform: serverless Lambda (V2)

> Status: production. Estimated cost: ~$0.55/month at ~100 requests/day (an estimate, not taken from an AWS bill).

The API gets hours or days between requests, so paying per millisecond of Lambda time costs far less than keeping a server running all day. The trade-off is a cold start on the first request after the function has been idle.

## Design decisions

| Decision | Reason |
|----------|--------|
| Lambda over ECS | ~97% cheaper (~$20 → ~$0.55/month) for this traffic |
| Function URL over API Gateway | No extra cost, simpler CORS |
| Container image over ZIP | Portability, easier dependency management |
| OIDC over access keys | No long-lived AWS credentials in CI/CD |
| On-demand DynamoDB | Pay per request instead of provisioned capacity |
| Terraform over SAM/CDK | Every resource written out in plain HCL |

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
│   │  │  -api-prod       │   Push   │  │ ┌───────────────┐   │   │       │   │
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
│   │   │  • Default SSE-S3     │           │  • UserId (PK)          │   │   │
│   │   │  • (not versioned)    │           │  • On-demand billing    │   │   │
│   │   └───────────────────────┘           │  • No TTL yet           │   │   │
│   │                                       └─────────────────────────┘   │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                             Observability                           │   │
│   │                                                                     │   │
│   │              /aws/lambda/boxdmetrics-api-prod                       │   │
│   │                └── 7-day log retention                              │   │
│   │                                                                     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Resources

### Compute

| Resource | Purpose | Configuration |
|----------|---------|---------------|
| `aws_ecr_repository.api` | Container image storage | AES256 encryption, scan on push, mutable tags |
| `aws_lambda_function.api` | Runs the API | 512 MB RAM, 30 s timeout, container image |
| `aws_lambda_function_url.api_url` | HTTPS endpoint | CORS restricted to listed origins |

### Data storage

The S3 bucket and DynamoDB table exist for planned persistence. The current API doesn't write to them.

| Resource | Purpose | Configuration |
|----------|---------|---------------|
| `aws_s3_bucket.csv_uploads` | Raw CSV storage | Default SSE-S3 encryption (applied by AWS), no versioning yet |
| `aws_dynamodb_table.user_movie_stats` | Cached stats | On-demand billing, string partition key, AWS-owned encryption |
| `aws_cloudwatch_log_group.api` | Execution logs | 7-day retention |

### IAM

| Resource | Purpose | Configuration |
|----------|---------|---------------|
| `data.aws_iam_openid_connect_provider.github` | Lets GitHub Actions log in | Existing provider, looked up with a `data` source (not created here) |
| `aws_iam_role.github_actions` | CI/CD deployment | Trust limited to this repository |
| `aws_iam_role_policy.github_actions_policy` | Deployment permissions | ECR and Lambda only |
| `aws_iam_role.lambda_execution_role` | Lambda runtime | CloudWatch, S3, DynamoDB |
| `aws_iam_policy.lambda_app_permissions` | App permissions | Only the bucket and table above |

### Terraform state

| Resource | Purpose | Configuration |
|----------|---------|---------------|
| `aws_s3_bucket.terraform_state` | State bucket | Versioned. Not configured as the backend yet: state is still local |
| `random_id.suffix` | Unique bucket names | 4 random bytes |

## Monthly cost

| Service | Estimate | Notes |
|---------|----------|-------|
| Lambda | $0.02 | Covered by the free tier |
| CloudWatch Logs | $0.50 | 7-day retention |
| DynamoDB | $0.00 | On-demand, almost no traffic |
| S3 | $0.01 | Under 1 GB, few requests |
| ECR | $0.00 | One small image, free tier |
| Data transfer | $0.02 | Outbound through the Function URL |
| Total | ~$0.55 | Grows with usage |

The estimate assumes ~100 requests/day at ~200 ms each.

The only cost limit in place is the 7-day log retention. Reserved concurrency, S3 lifecycle rules and AWS Budgets alerts are not set up yet.

## Deployment flow

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
       └── boxdmetrics-api-prod
```

- Every image is also tagged with its commit SHA, so an older version can be redeployed. The tags are mutable, though, so `latest` (and in principle a SHA tag) can be overwritten.
- The deploy only runs if every security check passes.
- CI logs in through OIDC; no AWS credentials are stored in the repository.
- Terraform state is local for now. Remote state with locking is planned.

## Security

### Function URL and CORS

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

CORS only controls what a browser lets a web page do. A page on another site can't read the API's responses, but a request sent with `curl` or a script, or any request that skips the preflight, still reaches Lambda and is billed. The rate limit and the API key below are the only other checks, and neither stops a determined caller (see [API key](../../README.md#api-key-not-a-secret) in the main README).

### Application (FastAPI)

```python
# Header-based API key validation
async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401)

# Rate limiting per IP
@limiter.limit("3/minute")
```

### IAM

| Role | Allowed actions | Resource |
|------|-----------------|----------|
| `lambda_execution` | `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` | CloudWatch only |
| `lambda_app` | `s3:PutObject`, `s3:GetObject` | The CSV bucket only |
| `lambda_app` | `dynamodb:PutItem`, `dynamodb:GetItem`, `dynamodb:UpdateItem`, `dynamodb:Query` | The stats table only |

The GitHub Actions role can push and pull images, create repositories named `boxdmetrics-api-*` in ECR, and update the code of this one Lambda function. It has no IAM permissions and can't delete resources.

### Other hardening

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

### API key

`api_secret_key` is marked `sensitive = true`, so Terraform hides it in plan output, and it reaches the function as a Lambda environment variable. FastAPI checks it on every request. The app must never log it or return it in an error message.

The frontend sends this key from the browser, so it is visible in the JavaScript bundle and is not a real secret. See [API key](../../README.md#api-key-not-a-secret) in the main README.

### Known gaps

A Semgrep scan of this directory flagged these, and they are still open:
- ECR tags are mutable (`image_tag_mutability = "MUTABLE"`).
- DynamoDB uses AWS-owned encryption, not a customer-managed KMS key.

The gaps in the application and the pipeline are listed in the [main README](../../README.md#known-gaps).

## Files

| File | Purpose | Main resources |
|------|---------|----------------|
| `main.tf` | Core infrastructure | Lambda, ECR, S3, DynamoDB, IAM roles |
| `oidc.tf` | GitHub Actions trust | OIDC provider, IAM assume policy |
| `providers.tf` | AWS configuration | eu-north-1, provider versions |
| `variables.tf` | Inputs | Environment, memory, secrets |
| `outputs.tf` | Outputs | Function URL, ECR repo, resources |
| `terraform.tfvars` | Real values; local only, not committed | |

## Related documentation

- [Monitoring: Prometheus + Grafana](../monitoring/)
- [Legacy: ECS architecture](../terraform-legacy/)
- [Main README](../../README.md)
