# Infrastructure - Current (V2)

> **Status:** Production
>
> Serverless-first architecture using AWS Lambda Function URLs.

## Philosophy

This architecture prioritizes **cost-efficiency** and **operational simplicity** over full-time availability. For an API with hours or days between requests, paying by millisecond is cheaper than 24/7 uptime.

## Architecture

```text
┌─────────────────────────────────────────────────────┐
│                   AWS Cloud                         │
│                                                     │
│  ┌──────────────────────────────────────────┐      │
│  │              ECR Registry                │      │
│  │  ┌─────────┐    ┌─────────┐             │      │
│  │  │ :latest │    │ :sha    │             │      │
│  │  │  (prod) │    │ (build) │             │      │
│  │  └────┬────┘    └─────────┘             │      │
│  │       │                                   │      │
│  └───────┼───────────────────────────────────┘      │
│          │                                           │
│          ▼                                           │
│  ┌──────────────────────────────────────────┐      │
│  │           Lambda Function                │      │
│  │  ┌────────────────────────────────────┐  │      │
│  │  │  Container Image                  │  │      │
│  │  │  - FastAPI + Mangum adapter       │  │      │
│  │  │  - 30s timeout / 512MB memory     │  │      │
│  │  └────────────────────────────────────┘  │      │
│  │             │                           │      │
│  │             ▼                           │      │
│  │  ┌───────────────────────────────────┐   │      │
│  │  │  Function URL (CORS-enabled)   │   │      │
│  │  │  ─────────────────────────────  │   │      │
│  │  │  Origin: Vercel production     │   │      │
│  │  │  Auth: NONE (app-level in code)   │   │      │
│  │  └───────────────────────────────────┘   │      │
│  └──────────────────────────────────────────┘      │
│          │                                           │
│          ▼                                           │
│  ┌─────────────────────────────────────────┐        │
│  │         Data Layer (Minimal)           │        │
│  │  ┌──────────────┐  ┌───────────────┐   │        │
│  │  │ S3 (CSV)     │  │ DynamoDB      │   │        │
│  │  │ Ephemeral    │  │ User caching  │   │        │
│  │  └──────────────┘  └───────────────┘   │        │
│  └─────────────────────────────────────────┘        │
│                                                     │
└─────────────────────────────────────────────────────┘

Security: IAM Role (least privilege)
Observability: CloudWatch Logs (7 day retention)
```

## Resources

```hcl
# Core compute
aws_ecr_repository.api
aws_lambda_function.api
aws_lambda_function_url.api_url

# Data
csv_uploads        (S3)
user_movie_stats (DynamoDB)

# Security
lambda_execution_role
s3_access_policy
dynamodb_access_policy

# DevOps
aws_cloudwatch_log_group.api
```

## Cost Breakdown

| Service | Monthly Estimate | Note |
|---------|------------------|------|
| **Lambda** | $0.02 | Free tier covers most usage |
| **CloudWatch** | $0.50 | 7-day retention minimal |
| **DynamoDB** | $0.00 | On-demand, low volume |
| **S3** | $0.01 | <1GB storage |
| **ECR** | $0.00 | Single image, small |
| **Total** | **~$0.55** | At current usage |

## Deployment Flow

```
GitHub Push
    │
    ▼ (GitHub Actions)
┌─────────────────────────────────────┐
│ 1. Security Scan                   │
│    - Bandit                        │
│    - Gitleaks                      │
│    - pip-audit                     │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 2. Build & Scan                    │
│    - Docker build                  │
│    - Trivy CVE scan                │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 3. Push ECR                        │
│    - Tag: SHA + latest             │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 4. Deploy Lambda                     │
│    - Update function code            │
│    - Cold start: ~1-2s               │
└─────────────────────────────────────┘
```

## Security Model

```
Layer 1: Lambda Function URL
  └── CORS restriction (Vercel origins only)
  └── auth_type = "NONE" (prevents AWS SigV4 issues)

Layer 2: Application Code
  └── X-API-Key header verification
  └── Rate limiting (slowapi)

Layer 3: IAM
  └── Task role with minimal permissions
  └── No public subnet access
```

## Files

- `main.tf` - Lambda, ECR, data stores
- `oidc.tf` - GitHub Actions IAM trust
- `providers.tf` - AWS provider config
- `variables.tf` - Environment inputs
- `outputs.tf` - Useful resource references

## When NOT to Use This

❌ High-traffic API ( sustained >100 req/s)
❌ Long-running processes (>30s)
❌ Microsecond-latency requirements
❌ Need persistent connections (WebSockets)

## Future Work

- [ ] Lambda provisioned concurrency (eliminate cold start)
- [ ] CloudWatch Alarms (error rate, latency)
- [ ] X-Ray tracing
