# Terraform Legacy: ECS Fargate Architecture (V1)

> **Status:** Deprecated / Archived
> **Migration:** Superseded by [Serverless Lambda (V2)](../terraform/)
> **Purpose:** Documentation of original infrastructure and evolution rationale

---

## Why This Exists

This directory preserves the **first iteration** of BoxdMetrics infrastructure: a traditional containerized approach using AWS ECS Fargate with [DuckDNS](https://www.duckdns.org/) for dynamic hostname resolution. It serves as architecture documentation showing the evolution from always-on compute to serverless-first design.

### Migration Rationale

| Metric | ECS (V1) | Lambda (V2) | Savings |
|--------|----------|-------------|---------|
| Monthly Cost | ~$20-35 | ~$0.55 | **98.4%** |
| Complexity | VPC + DuckDNS + ECS | Function URL | **Simplified** |
| Scaling | Manual config | Automatic | **Better** |
| Cold Start | 2-5s (container) | 1-2s (Lambda) | **Comparable** |

**Note:** Used DuckDNS instead of ALB to avoid ~$16/mo load balancer cost.

---

## Architecture (ECS Fargate with DuckDNS)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                 AWS Cloud                                   │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                         VPC (10.10.10.0/24)                         │   │
│   │                                                                     │   │
│   │  ┌──────────────────────────┐         ┌──────────────────────────┐  │   │
│   │  │       Public Subnet      │         │       ECS Cluster        │  │   │
│   │  │      (10.10.10.0/25)     │         │                          │  │   │
│   │  │                          │         │   ┌──────────────────┐   │  │   │
│   │  │  ┌────────────────────┐  │         │   │   Fargate Task   │   │  │   │
│   │  │  │    Internet GW     │──┼───────▶ │   │  ┌────────────┐  │   │  │   │
│   │  │  └─────────┬──────────┘  │         │   │  │  FastAPI   │  │   │  │   │
│   │  │            │             │         │   │  │ Container  │  │   │  │   │
│   │  │  ┌─────────▼──────────┐  │         │   │  └────────────┘  │   │  │   │
│   │  │  │   Public IP:8000   │  │         │   └──────────────────┘   │  │   │
│   │  │  └─────────┬──────────┘  │         └──────────────────────────┘  │   │
│   │  └────────────┼─────────────┘                                       │   │
│   └───────────────┼─────────────────────────────────────────────────────┘   │
│                   │                                                         │
│   ┌───────────────▼──────────┐            ┌──────────────────────────┐      │
│   │        DuckDNS           │            │        Data Layer        │      │
│   │  ──────────────────────  │            │  ┌────────────────────┐  │      │
│   │  boxdmetrics-api...      │            │  │  S3 (CSV Uploads)  │  │      │
│   │  (Dynamic IP Sync)       │            │  │  DynamoDB (Stats)  │  │      │
│   └──────────────────────────┘            │  └────────────────────┘  │      │
│                                           └──────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Networking:** No ALB. Container gets public IP directly, DuckDNS client updates hostname.

---

## Components

| Resource | Purpose | V2 Replacement |
|----------|---------|----------------|
| `aws_vpc.main_vpc` | Isolated network (10.10.10.0/24) | Lambda networking (ephemeral) |
| `aws_subnet.public_subnet` | Container hosting subnet | Lambda (no subnet management) |
| `aws_internet_gateway.igw` | Public internet access | Lambda function URL |
| `aws_security_group.web_sg` | Firewall rules (port 8000) | IAM policies |
| `aws_ecs_cluster.main` | Container orchestration | Lambda (no cluster needed) |
| `aws_ecs_service.api` | Task scheduling | Lambda (event-driven scaling) |
| `aws_ecs_task_definition.api` | Container spec with DuckDNS env vars | Docker image in Lambda |
| `aws_iam_role.ecs_execution_role` | Task execution permissions | Lambda execution role |
| `aws_iam_role.ecs_task_role` | Container permissions | Lambda IAM role |
| `aws_cloudwatch_log_group.api` | Log aggregation | CloudWatch (native) |
| DuckDNS (external) | Dynamic hostname for public IP | Lambda function URL (built-in) |

---

## Security Model (V1)

```
Layer 1: Security Group
├── Ingress: Port 8000 from 0.0.0.0/0 (world-accessible API)
├── Egress: All traffic allowed
└── Risk: Container directly exposed to internet

Layer 2: IAM Roles
├── ecs-execution-role: Pull from ECR, CloudWatch logging
└── ecs-task-role: Access S3, DynamoDB

Layer 3: Container Hardening
├── Non-root user (appuser)
├── DuckDNS client updates dynamic IP
└── HTTP only (no TLS termination)
```

**Security Tradeoffs vs V2:**
- Public subnet required with public IPs
- Container directly exposed (no ALB/proxy)
- HTTP only (no HTTPS) - DuckDNS doesn't support TLS
- Dynamic IP changes on redeployment
- VPC network ACLs needed for defense in depth

---

## Configuration

### Required Variables

```hcl
# Environment
environment    = "dev"  # dev | prod

# Rightsizing
task_cpu       = 256   # 0.25 vCPU - minimum Fargate
task_memory    = 512   # MB - minimum for Python + Pandas

# Secrets (see secrets.auto.tfvars - NEVER commit)
api_secret_key = var.api_secret_key  # FastAPI auth
duckdns_token  = var.duckdns_token   # Dynamic DNS (deprecated)
```

### DuckDNS Integration

```hcl
# Container environment variables
environment = [
  {
    name  = "DUCKDNS_DOMAIN"
    value = "boxdmetrics-api"
  },
  {
    name  = "DUCKDNS_TOKEN"
    value = var.duckdns_token
  }
]
```

The application code would update DuckDNS with the container's public IP on startup.

---

## Lessons Learned: ECS vs Lambda

### ECS with DuckDNS Pros

- ✅ No cold starts after initial container startup
- ✅ Familiar container deployment model
- ✅ **No ALB cost** (DuckDNS workaround)
- ✅ Predictable pricing at steady-state
- ✅ Static container for hours/days

### ECS with DuckDNS Cons

- ❌ Container exposed to internet (security)
- ❌ ~~HTTP only~~ **SOLVED:** Vercel proxy added HTTPS
- ❌ Dynamic IP on redeployment
- ❌ DuckDNS dependency (external service)
- ❌ Proxy adds latency (Vercel → DuckDNS)
- ❌ Still expensive for low-traffic (~$24/mo)
- ❌ No scale-to-zero
- ❌ More complexity than Lambda

### Lambda Pros (Current)

- ✅ HTTPS included (Function URL)
- ✅ No public IP exposure
- ✅ 98% cost reduction
- ✅ Auto-scaling to zero

### Lambda Trade-offs

- ⚠️ Cold starts
- ⚠️ 30-second timeout limit

---

## Files

| File | Purpose |
|------|---------|
| `main-legacy.tf` | ECS cluster, service, task definitions with DuckDNS env vars |
| `variables.tf` | Environment configuration inputs |
| `secrets.auto.tfvars` | **NOT COMMITTED** - DuckDNS token, API secrets |
| `.terraform/` | Provider modules and state cache |
| `terraform.tfstate` | **Local only** - no S3 backend in V1 |

---

## When to Use ECS

Even with DuckDNS, this architecture is superior when:

- Sustained >100 requests/second traffic
- Long-running processes (>30 seconds average)
- Need persistent connections (WebSockets)
- VPC-native service integration required (RDS, ElastiCache)
- **ALB acceptable cost** (steady traffic makes it worthwhile)
- Compliance mandates static IPs
