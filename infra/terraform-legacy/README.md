# Terraform legacy: ECS Fargate (V1)

> Status: archived. Replaced by the [serverless Lambda version (V2)](../terraform/).

This was the first version of the BoxdMetrics infrastructure: the FastAPI container ran on AWS ECS Fargate, and [DuckDNS](https://www.duckdns.org/) gave its changing public IP a stable hostname. It stays here to show what the project ran on before Lambda and why it moved.

## Why it moved to Lambda

| Metric | ECS (V1) | Lambda (V2) | Change |
|--------|----------|-------------|--------|
| Monthly cost | ~$20-35 | ~$0.55 | 97-98% cheaper |
| Moving parts | VPC + DuckDNS + ECS | Function URL | Fewer |
| Scaling | Configured by hand | Automatic, down to zero | |
| Cold start | 2-5 s (container) | ~10 s observed (Lambda) | Slower |

DuckDNS was used instead of an Application Load Balancer, which would have cost about $16/month on its own.

## Architecture

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

There was no load balancer. The container got a public IP directly, and a DuckDNS client updated the hostname.

## Resources

| Resource | Purpose | V2 replacement |
|----------|---------|----------------|
| `aws_vpc.main_vpc` | Isolated network (10.10.10.0/24) | None; Lambda needs no VPC |
| `aws_subnet.public_subnet` | Subnet for the container | None |
| `aws_internet_gateway.igw` | Public internet access | Lambda Function URL |
| `aws_security_group.web_sg` | Firewall rules (port 8000) | IAM policies |
| `aws_ecs_cluster.main` | Container orchestration | None |
| `aws_ecs_service.api` | Task scheduling | Lambda's own scaling |
| `aws_ecs_task_definition.api` | Container spec with DuckDNS env vars | Container image in Lambda |
| `aws_iam_role.ecs_execution_role` | Task execution permissions | Lambda execution role |
| `aws_iam_role.ecs_task_role` | Container permissions | Lambda IAM role |
| `aws_cloudwatch_log_group.api` | Logs | Lambda's CloudWatch log group |
| DuckDNS (external) | Hostname for the public IP | Function URL (built in) |

## Security model

```
Layer 1: Security Group
├── Ingress: Port 8000 from 0.0.0.0/0 (world-accessible API)
├── Egress: All traffic allowed
└── Risk: Container directly exposed to internet

Layer 2: IAM Roles
├── ecs-execution-role: Pull from ECR, CloudWatch logging
└── ecs-task-role: Access S3, DynamoDB

Layer 3: Container
├── DuckDNS client updates dynamic IP
└── HTTP only (no TLS termination)
```

Compared with V2, this setup:
- needed a public subnet and public IPs,
- exposed the container directly, with no load balancer or proxy in front,
- served plain HTTP, because DuckDNS doesn't provide TLS,
- changed IP on every redeploy,
- would have needed network ACLs as a second line of defence.

## Configuration

### Variables

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

### DuckDNS

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

On startup the application sent the container's public IP to DuckDNS.

## ECS vs Lambda

What ECS with DuckDNS did well:
- No cold starts once the container was up.
- A familiar container deployment model.
- No load balancer cost, thanks to DuckDNS.
- Predictable cost under steady traffic.

Where it fell short:
- The container was exposed to the internet.
- It served plain HTTP until a Vercel proxy was added in front for HTTPS, and that proxy added latency.
- The IP changed on every redeploy.
- It depended on DuckDNS, an outside service.
- It still cost about $24/month with almost no traffic, because it couldn't scale to zero.

What Lambda (current) changes:
- HTTPS comes with the Function URL.
- No public IP to expose.
- About 97% cheaper.
- Scales to zero.

The costs of Lambda are cold starts and the 30-second timeout set on the function (Lambda allows up to 15 minutes).

## Files

| File | Purpose |
|------|---------|
| `main-legacy.tf` | ECS cluster, service and task definition with DuckDNS env vars |
| `variables.tf` | Inputs |
| `secrets.auto.tfvars` | Not committed: DuckDNS token and API secret |
| `.terraform/` | Provider plugins and module cache |
| `terraform.tfstate` | Local only; V1 had no S3 backend |

## When ECS is the better choice

ECS still beats Lambda when the service has:
- sustained traffic above about 100 requests per second,
- requests that run longer than 15 minutes, the Lambda maximum,
- persistent connections such as WebSockets,
- other VPC services to talk to, such as RDS or ElastiCache,
- enough steady traffic to justify a load balancer,
- a compliance rule that requires static IPs.
