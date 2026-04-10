# Monitoring & Observability

Local development monitoring stack using Prometheus + Grafana.

## Why This Exists

Production uses CloudWatch (Lambda-native). This setup enables **local performance testing** and **development debugging**.

## Stack

```text
┌──────────────────────────────────────────────────┐
│              Docker Compose                      │
│                                                  │
│   ┌─────────┐    ┌──────────┐   ┌──────────┐   │
│   │ Backend │───▶│ Prometheus │───▶│ Grafana  │   │
│   │ :8000   │    │  :9090    │   │  :3000   │   │
│   └────┬────┘    └──────────┘   └──────────┘   │
│        │                                          │
│        │  /metrics (Prometheus format)           │
│        │                                          │
│   ┌────▼────┐                                    │
│   │  Redis  │  (Rate limiting storage)          │
│   │ :6379   │                                    │
│   └─────────┘                                    │
└──────────────────────────────────────────────────┘
```

## Services

### Prometheus (:9090)

Scrapes FastAPI metrics via `prometheus-fastapi-instrumentator`.

**Key metrics:**
- `http_requests_total` - Request counter
- `http_request_duration_seconds` - Latency histogram
- `process_memory_bytes` - Memory usage (leak detection)
- `process_open_fds` - File descriptor tracking

**Config:** `prometheus.yml`

```yaml
scrape_configs:
  - job_name: 'boxdmetrics-api'
    static_configs:
      - targets: ['backend:8000']
    scrape_interval: 15s
```

### Grafana (:3000)

Visualizes Prometheus data. Common dashboards:

| Dashboard | Use Case |
|-----------|----------|
| **Request Rate** | RPS over time |
| **Response Time** | p50/p95/p99 latency |
| **Memory Growth** | Detect DataFrame leaks |
| **Error Rate** | 4xx/5xx breakdown |

**Access:** http://localhost:3000 (admin/admin)

## Usage

```bash
# Start stack
cd /home/paulo/BoxdMetrics
docker-compose up -d

# View Prometheus targets
curl http://localhost:9090/api/v1/targets

# Query metrics directly
curl http://localhost:8000/metrics
```

## Production Note

CloudWatch equivalent metrics:

| Local (Prometheus) | Production (CloudWatch) |
|--------------------|------------------------|
| `http_requests_total` | `AWS/Lambda: Invocations` |
| `http_request_duration` | `AWS/Lambda: Duration` |
| `process_memory_bytes` | `AWS/Lambda: MemorySize`, UsedMemory |
| Custom errors | `CloudWatch Logs Insights` |

## Memory Debugging

Pandas can leak memory with large DataFrames. Monitor with:

```promql
# Memory growth over 5m
rate(process_memory_bytes[5m])

# If consistently rising → check DataFrame cleanup
```

## Files

- `prometheus.yml` - Scrape configuration
