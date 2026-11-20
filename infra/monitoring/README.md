# Monitoring

Locally, Prometheus scrapes the FastAPI backend and Grafana shows the results. In production the backend runs on Lambda, which sends its metrics to CloudWatch on its own.

| Environment | Tooling | Used for |
|-------------|---------|----------|
| Development | Prometheus + Grafana | Debugging and performance tuning while coding |
| Production | AWS CloudWatch | Lambda's built-in metrics and logs, no extra servers |

## Local stack

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

Ports:
- `http://localhost:8000`: FastAPI backend
- `http://localhost:9090`: Prometheus query UI
- `http://localhost:3000`: Grafana dashboards (anonymous access with the Admin role)

## Prometheus (port 9090)

Prometheus scrapes the backend every 15 seconds. The backend exposes its metrics through `prometheus-fastapi-instrumentator`.

### Metrics exposed

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

### Query examples

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

## Grafana (port 3000)

```bash
# Start stack
docker-compose up -d

# Open Grafana
open http://localhost:3000
# Login: admin / admin (accept password change prompt)
```

Docker Compose turns on anonymous access with the Admin role, so the dashboards open without logging in. The `admin`/`admin` login above is only needed for the account itself. Keep this stack on your own machine.

### AppHealth dashboard (`AppHealth.json`)

RED metrics (rate, errors, duration): what users of the API notice.

| Panel | Query | What it shows |
|-------|-------|---------------|
| Error Rate | `http_requests_total{status=~"4xx\|5xx"}` | Bad uploads (400s) and crashes (500s) |
| Requests/sec | `rate(http_requests_total)` | API throughput over time |
| Avg Duration | `rate(duration_sum) / rate(duration_count)` | Average API latency |
| P95 Latency | `histogram_quantile(0.95, ...)` | 95% of requests are faster than this line |

Useful while load testing, to catch performance regressions, and to spot error spikes by eye (there are no alerts).

### Infrastructure dashboard (`Infrastructure.json`)

USE metrics (utilization, saturation, errors), for finding resource bottlenecks.

| Panel | Query | What it shows |
|-------|-------|---------------|
| CPU Usage | `rate(process_cpu_seconds_total[5m]) * 100` | Container CPU use |
| Container Restarts | `changes(process_start_time_seconds[24h])` | How many times the process restarted |
| Memory Usage | `deriv(process_resident_memory_bytes[5m])` | Memory growth rate |

A memory growth rate that stays positive points to a leak, for example Pandas DataFrames that are never released:

```promql
# In Grafana - Memory Usage panel
# Rate of change positive = leak
deriv(process_resident_memory_bytes{job="boxdmetrics-api"}[5m])
```

Every panel on this dashboard turns red at 80.

## Production: CloudWatch

Lambda sends these metrics to CloudWatch without any setup:

```
Lambda Execution
│
├─ Invocation Count ──> AWS/Lambda: Invocations
├─ Duration ──────────> AWS/Lambda: Duration
├─ Errors ──────────> AWS/Lambda: Errors
├─ Memory Used ─────> CloudWatch Logs: REPORT line
└─ Custom Logs ───────> CloudWatch Logs: /aws/lambda/*
```

### Local metric to CloudWatch equivalent

| Local (Prometheus) | Production (CloudWatch) | Where |
|--------------------|-------------------------|-------|
| `http_requests_total` | `AWS/Lambda: Invocations` | Console |
| `http_request_duration_seconds` | `AWS/Lambda: Duration` | Console |
| `process_resident_memory_bytes` | `Max Memory Used` in the REPORT line | Logs |
| Custom errors | Logs Insights query | CloudWatch |

### CloudWatch Logs Insights queries

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

## Alerting

There are no alerts yet, locally or in production. These are the thresholds to watch for by hand on the local dashboards:

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Error rate | > 1% | > 5% | Check logs |
| P95 latency | > 1 s | > 5 s | Optimize code |
| Memory growth | > 50 MB/5m | > 100 MB/5m | Check DataFrame cleanup |
| CPU | > 80% | > 95% | Look for infinite loops |

A production alarm would look like this (not implemented):

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

## Files

| File | Purpose |
|------|---------|
| `prometheus.yml` | Scrape configuration (15 s interval) |
| `grafana/AppHealth.json` | RED metrics dashboard |
| `grafana/Infrastructure.json` | USE metrics dashboard |
| `grafana/provisioning/datasources/datasource.yml` | Connects Grafana to Prometheus on startup |
| `grafana/provisioning/dashboards/provider.yml` | Loads the dashboards on startup |

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

## Local vs production

| | Local (Prometheus) | Production (CloudWatch) |
|---|---|---|
| Cost | Free (containers) | ~$0.50/month (logs) |
| Delay | Under a second | About 1 to 5 minutes |
| Retention | Lost when the containers are removed | 7 days (configurable) |
| Queries | PromQL | CloudWatch Logs Insights |
| Dashboards | Grafana | Basic CloudWatch console |
| Alerting | None (watch the dashboards) | None yet; CloudWatch alarms can notify through SNS |
| Cold starts | Not applicable (the container stays up) | `Init Duration` in the REPORT log line |

## Related documentation

- [Main project README](../../README.md)
- [Terraform infrastructure](../terraform/)
- [Legacy ECS architecture](../terraform-legacy/)
