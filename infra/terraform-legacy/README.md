# Infrastructure - Legacy (V1)

> **Status:** Deprecated (Migrated to Lambda in 2024)
>
> This directory documents the original ECS-based architecture. Kept for reference and to show design evolution.

## Why This Existed

The initial architecture followed traditional container deployment patterns.

## Architecture

```text
┌─────────────────────────────────────────────────────┐
│                   AWS Cloud                         │
│                                                     │
│  ┌──────┐  ┌─────────────┐  ┌──────────────────┐   │
│  │ ECR  │──▶│ ECS Cluster │──▶│ Application LB │  │
│  └──┬───┘  └─────────────┘  └──────────────────┘   │
│     │         │                                    │
│     │    ┌────▼────┐   ┌─────────────────────┐    │
│     │    │  Tasks  │───▶│ VPC (3 AZs)         │    │
│     │    │  (Fargate) │  │ - Public subnets    │    │
│     │    └──────   │   │ - Private subnets   │    │
│     │              │   │ - NAT Gateway       │    │
│     │    ┌─────────┼───▶└─────────────────────┘    │
│     │    │         │                               │
│     ▼    ▼         ▼                               │
│  ┌─────────────────────┐                           │
│  │  Data Layer         │                           │
│  │  - S3 (CSV exports) │                           │
│  │  - DynamoDB (stats) │                           │
│  └─────────────────────┘                           │
└─────────────────────────────────────────────────────┘
```

## Components

| Service | Purpose | Monthly Cost |
|---------|---------|--------------|
| **VPC** | Network isolation with 3 AZs | ~$30-50 |
| **NAT Gateway** | Outbound internet for private subnets | ~$32 |
| **ECS Fargate** | Container orchestration | ~$20-40 |
| **ALB** | HTTP load balancing | ~$16 |
| **S3** | CSV file storage | ~$0-1 |
| **DynamoDB** | Processed stats (on-demand) | ~$0-5 |

**Total: ~$100-150/month**

## Migration Decision

### Pain Points

| Issue | Impact |
|-------|--------|
| Cold starts | No real "cold start" but container startup ~2-5s |
| Idle costs | $100+/month even with 0 traffic |
| VPC complexity | NAT, IGW, route tables, security groups |
| Scaling | Need to configure task auto-scaling |
| Certificate management | TLS termination at ALB, cert renewal |

### Migration Path

```
ECS + VPC + ALB
      │
      ▼
Dockerfile.lambda + Mangum
      │
      ▼
Lambda Function URL

Benefits:
- Cost: $100 → $0.02/month (scales to zero)
- Latency: 2-5s → <100ms (provisioned concurrency)
- Complexity: 15+ resources → 5 resources
- Security: No public VPC, no LB exposure
```

## Files

- `main-legacy.tf` - ECS cluster, services, tasks
- `network-legacy.tf` - VPC, subnets, routing (if exists)
- `.terraform/` - Managed externally (S3 backend)

## Learning Outcome

✅ **Proved:** Serverless is viable for API workloads with sporadic traffic  
✅ **Trade-off:** Added cold start concern (mitigated with provisioned)  
✅ **Kept:** Same container packaging (portability maintained)
