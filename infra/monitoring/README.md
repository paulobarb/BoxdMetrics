# Monitoring & Observability

> Local development monitoring stack using Prometheus + Grafana.  
> Production uses AWS CloudWatch (Lambda-native).

---

## Philosophy

Two observability paths for two different needs:

| Environment | Tooling | Purpose |
|-----------|---------|---------|
| **Development** | Prometheus + Grafana | Real-time debugging, performance tuning |
| **Production** | AWS CloudWatch | Cost-efficient, serverless-native metrics |

---

## Local Development Stack

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Docker Compose Network                           │
│                                                                         │
│      ┌──────────┐     ┌──────────────┐     ┌──────────────┐             │
│      │          │     │              │     │              │             │
│      │ Backend  │────>│  Prometheus  │────>│   Grafana    │             │
│      │  :8000   │     │   :9090      │     │   :3000      │             │
│      │          │     │              │     │              │             │
│      └────┬─────┘     └──────────────┘     └──────────────┘             │
│           │                                                             │
│           │ /metrics endpoint                                           │
│      ┌────┴────┐                                                        │
│      │  Redis  │                  Rate limiting storage                 │
│      │  :6379  │                  (not monitored here)                  │
│      └─────────┘                                                        │
└─────────────────────────────────────────────────────────────────────────┘
```

**Ports:**
- `http://localhost:8000` - FastAPI backend
- `http://localhost:9090` - Prometheus query UI
- `http://localhost:3000` - Grafana dashboards (admin/admin)

---

## Prometheus (Port 9090)

Scrapes FastAPI metrics every 15 seconds via `prometheus-fastapi-instrumentator`.

### Metrics Exposed

| Metric | Type | Description |
|--------|------|-------------|
| `http_requests_total` | Counter | Total requests by handler, method, status |
| `http_request_duration_seconds` | Histogram | Request latency distribution |
| `http_request_duration_seconds_bucket` | Histogram | Bucketed latency for percentiles |
| `process_resident_memory_bytes` | Gauge | Memory usage (RAM) |
| `process_cpu_seconds_total` | Counter | CPU time consumed |
| `process_open_fds` | Gauge | Open file descriptors |
| `process_start_time_seconds` | Gauge | Process start timestamp |

### Configuration

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'boxdmetrics-api'
    static_configs:
      - targets: ['backend:8000']
    scrape_interval: 15s
```

### Query Examples

```promql
# Request rate per second
rate(http_requests_total[5m])

# 95th percentile latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate (4xx + 5xx)
rate(http_requests_total{status=~"4xx|5xx"}[5m])

# Memory growth detection
deriv(process_resident_memory_bytes[5m])
```

---

## Grafana (Port 3000)

Interactive dashboards for development debugging.

### Access

```bash
# Start stack
docker-compose up -d

# Open Grafana
open http://localhost:3000
# Login: admin / admin (accept password change prompt)
```

### Dashboards

#### 1. AppHealth (`AppHealth.json`)

**Purpose:** RED Metrics (Rate, Errors, Duration) — what end-users experience

**Panels:**

| Panel | Query | Interpretation |
|-------|-------|----------------|
| **Error Rate** | `http_requests_total{status=~"4xx\|5xx"}` | Volume of bad uploads (400s) and crashes (500s) |
| **Requests/sec** | `rate(http_requests_total)` | API throughput and load over time |
| **Avg Duration** | `rate(duration_sum) / rate(duration_count)` | User-perceived API latency |
| **P95 Latency** | `histogram_quantile(0.95, ...)` | 95% of requests faster than this line |

**Use cases:**
- Load testing visualization
- Performance regression detection
- Error spike alerting (manual)

#### 2. Infrastructure (`Infrastructure.json`)

**Purpose:** USE Metrics (Utilization, Saturation, Errors) — debugging resource bottlenecks

**Panels:**

| Panel | Query | Interpretation |
|-------|-------|----------------|
| **CPU Usage** | `rate(process_cpu_seconds_total[5m]) * 100` | Container CPU consumption |
| **Container Restarts** | `changes(process_start_time_seconds[24h])` | How many times process restarted (instability detection) |
| **Memory Usage** | `deriv(process_resident_memory_bytes[5m])` | Memory growth rate (leak detection) |

**Use cases:**
- Memory leak detection (Pandas DataFrame cleanup)
- Container health monitoring
- Resource profiling during dev

---

## Dashboard JSON Reference

### AppHealth.json

**Description:** Tracks RED Metrics for user experience monitoring

**File:** [`grafana/AppHealth.json`](grafana/AppHealth.json)

**Datasource:** Prometheus (preconfigured uid)

### Infrastructure.json

**Description:** Tracks USE Metrics for system health debugging

**File:** [`grafana/Infrastructure.json`](grafana/Infrastructure.json)

**Thresholds:**
- Green: 0-40%
- Red: > 80%

---

## Production: CloudWatch

Lambda automatically sends metrics to CloudWatch. No local Prometheus/Grafana needed.

### CloudWatch Metrics Path

```
Lambda Execution
│
├─ Invocation Count ──> AWS/Lambda: Invocations
├─ Duration ──────────> AWS/Lambda: Duration
├─ Errors ──────────> AWS/Lambda: Errors
├─ Memory Used ─────> CloudWatch Logs: REPORT line
└─ Custom Logs ───────> CloudWatch Logs: /aws/lambda/*
```

### Metric Mappings

| Local (Prometheus) | Production (CloudWatch) | Access |
|-------------------|------------------------|---------|
| `http_requests_total` | `AWS/Lambda: Invocations` | Console |
| `http_request_duration_seconds` | `AWS/Lambda: Duration` | Console |
| `process_memory_bytes` | `Memory Size` - `Max Memory Used` | Logs |
| Custom errors | Logs Insights query | CloudWatch |

### Useful CloudWatch Queries

```sql
-- Lambda execution duration
fields @timestamp, @duration
| filter @type = "REPORT"
| stats avg(@duration), max(@duration), pct(@duration, 95) by bin(5m)

-- Memory usage
fields @timestamp, @memorySize, @maxMemoryUsed
| filter @type = "REPORT"
| stats avg(@maxMemoryUsed), max(@maxMemoryUsed) by bin(5m)

-- Error analysis
fields @timestamp, @message
| filter @message like /ERROR/
| stats count() by bin(1m)
```

---

## Alerting (Manual for now)

### Local Development Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Error rate | > 1% | > 5% check logs |
| P95 Latency | > 1s | > 5s optimize code |
| Memory growth | > 50MB/5m | > 100MB/5m check DataFrame cleanup |
| CPU | > 80% | > 95% investigate infinite loops |

### Production CloudWatch Alarms (Future)

```hcl
# Example alarm structure (not yet implemented)
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "boxdmetrics-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "Lambda error rate exceeded"
}
```

---

### Identifying Leaks (Local)

Pandas can leak memory with large DataFrames:

```promql
# In Grafana - Memory Usage panel
# Rate of change positive = leak
deriv(process_resident_memory_bytes{job="boxdmetrics-api"}[5m])
```

---

## Files

| File | Purpose |
|------|---------|
| `prometheus.yml` | Scraping configuration (15s interval) |
| `grafana/AppHealth.json` | RED metrics dashboard (user experience) |
| `grafana/Infrastructure.json` | USE metrics dashboard (system resources) |
| `grafana/provisioning/datasources/datasource.yml` | Auto-configured Prometheus connection |
| `grafana/provisioning/dashboards/provider.yml` | Auto-loaded dashboard definitions |

---

## Usage

```bash
# Start everything
docker-compose up -d

# View targets
open http://localhost:9090/targets

# Query metrics
open http://localhost:9090/graph

# View dashboards
open http://localhost:3000

# Stop stack
docker-compose down

# View logs
docker-compose logs -f prometheus
docker-compose logs -f grafana
```

---

## Comparison: Local vs Production

| Feature | Local (Prometheus) | Production (CloudWatch) |
|---------|-------------------|------------------------|
| **Cost** | Free (containers) | ~$0.50/mo (logs) |
| **Latency** | Real-time (<1s) | ~1-5 minute delay |
| **Retention** | Ephemeral (container lifetime) | 7 days (configurable) |
| **Queries** | PromQL | CloudWatch Logs Insights |
| **Dashboards** | Rich (Grafana) | Basic |
| **Alerting** | Manual (view dashboards) | SNS (configurable) |
| **Cold start tracing** | Yes (process_start_time) | No (only duration) |

---

## Related Documentation

- [Main Project README](../../README.md) - Architecture overview
- [Terraform Infrastructure](../terraform/) - AWS resources
- [Legacy ECS Architecture](../terraform-legacy/) - Original design
