# Skill: Grafana Observability

> Connects to Grafana to pull real traffic baselines, existing dashboards, and alert rules for services in the ADLC pipeline. Validates PRD traffic estimates against production reality. Provisions dashboards and alert rules from Build Brief throughput SLOs. Long-term, feeds live metrics into failure detection, capacity planning, and anomaly alerting across all services.

---

## Why This Exists

Without real observability data, the ADLC pipeline operates on estimates:
- **PRD traffic estimates** are guesses — often wrong by 2-10x
- **SLO targets** are set without knowing current baselines
- **Alert thresholds** are static numbers that don't account for time-of-day patterns
- **Failure detection** relies on error rates and latency alone — missing the earliest signal (traffic anomalies)
- **Incident runbooks** link to dashboards that may not exist or may be stale

This skill bridges the gap between "what we think traffic looks like" and "what Grafana actually shows." It runs at two points in the pipeline:

1. **Planning phase:** Pulls baselines to validate PRD estimates and pre-fill throughput SLOs with real data
2. **Deploy phase:** Provisions dashboards and alert rules so the feature is observable from day one

Long-term, this skill enables:
- **Automated anomaly detection** per service based on historical traffic patterns
- **Capacity planning triggers** when services approach their throughput ceilings
- **Cross-service traffic correlation** to detect cascading failures
- **Alert lifecycle management** — creating, updating, and retiring alerts as features evolve

---

## Trigger

| When | What | Mode |
|------|------|------|
| ADLC Planning Phase (after Codebase Research) | Pull traffic baselines and existing observability state for affected services | `baseline` |
| ADLC Phase 6 (SLOs) | Validate PRD throughput estimates against Grafana reality | `validate` |
| ADLC Deploy Phase (post-pipeline, parallel with Runbook) | Provision dashboards and alert rules from Build Brief throughput SLOs | `provision` |
| On-demand (periodic) | Refresh traffic baselines for a service to update anomaly detection thresholds | `refresh` |
| On-demand (investigation) | Pull current metrics for a service during incident response or capacity review | `query` |

---

## Input Contract

```json
{
  "grafana_url": "string (Grafana instance URL — e.g., https://grafana.company.com)",
  "grafana_api_token": "string (via MCP server auth — Service Account token with Viewer or Editor role)",
  "mode": "baseline | validate | provision | refresh | query",
  "services": [
    {
      "name": "string (service name as it appears in Grafana — e.g., 'api-server', 'widget-service')",
      "namespace": "string (optional — Kubernetes namespace or environment label)",
      "datasource": "string (optional — specific Grafana datasource to query, e.g., 'Prometheus', 'CloudWatch')"
    }
  ],
  "prd_traffic_estimates": {
    "launch_rps": "number (optional — from PRD Traffic & Load Expectations)",
    "steady_state_rps": "number (optional)",
    "peak_rps": "number (optional)",
    "polling_interval_seconds": "number (optional)",
    "traffic_pattern": "string (optional — steady | bursty | time-of-day | event-driven)"
  },
  "build_brief_slos": {
    "throughput_slos": "array (optional — from Build Brief Section 6, for provision mode)",
    "failure_modes": "array (optional — traffic-based failure modes from Section 4)"
  },
  "time_range": {
    "from": "string (ISO 8601 — default: 7 days ago)",
    "to": "string (ISO 8601 — default: now)"
  },
  "output_config": {
    "dashboard_folder": "string (optional — Grafana folder for provisioned dashboards)",
    "alert_notification_channel": "string (optional — Slack channel or PagerDuty service for alerts)",
    "alert_format": "grafana_native | prometheus_rules | both"
  }
}
```

---

## Output Contract

### Mode: `baseline`

```json
{
  "service_baselines": [
    {
      "service": "string",
      "time_range": {"from": "ISO date", "to": "ISO date"},
      "traffic_profile": {
        "avg_rps": "number",
        "p50_rps": "number",
        "p95_rps": "number",
        "p99_rps": "number",
        "peak_rps": "number",
        "peak_time": "ISO date",
        "min_rps": "number",
        "min_time": "ISO date",
        "daily_pattern": {
          "description": "string (e.g., 'traffic peaks 9am-5pm EST, drops 80% overnight')",
          "hourly_averages": [
            {"hour": 0, "avg_rps": "number"},
            {"hour": 1, "avg_rps": "number"}
          ]
        },
        "weekly_pattern": {
          "description": "string (e.g., 'weekday traffic 3x weekend')",
          "daily_averages": [
            {"day": "monday", "avg_rps": "number"},
            {"day": "tuesday", "avg_rps": "number"}
          ]
        },
        "traffic_classification": "steady | bursty | time-of-day | event-driven"
      },
      "latency_profile": {
        "p50_ms": "number",
        "p95_ms": "number",
        "p99_ms": "number",
        "max_ms": "number"
      },
      "error_profile": {
        "error_rate_percent": "number",
        "dominant_error_codes": [
          {"code": "number (e.g., 500, 429, 503)", "percentage": "number"}
        ]
      },
      "existing_dashboards": [
        {
          "uid": "string",
          "title": "string",
          "url": "string",
          "panels_relevant_to_feature": ["string (panel titles)"]
        }
      ],
      "existing_alerts": [
        {
          "uid": "string",
          "title": "string",
          "condition": "string",
          "state": "ok | alerting | pending | no_data",
          "notification_channels": ["string"]
        }
      ]
    }
  ],
  "generated_at": "ISO date",
  "grafana_instance": "string"
}
```

### Mode: `validate`

```json
{
  "validation_results": [
    {
      "service": "string",
      "prd_estimate": {
        "field": "string (e.g., 'steady_state_rps')",
        "value": "number",
        "basis": "string (from PRD)"
      },
      "grafana_actual": {
        "metric": "string",
        "value": "number",
        "time_range": "string"
      },
      "verdict": "aligned | optimistic | pessimistic | no_data",
      "deviation_percent": "number",
      "recommendation": "string (e.g., 'PRD estimates 200 RPS but Grafana shows current baseline at 450 RPS — adjust upward')"
    }
  ],
  "overall_assessment": "string",
  "missing_baselines": [
    {
      "service": "string",
      "reason": "no_dashboard | no_metrics | service_not_found",
      "recommendation": "string"
    }
  ]
}
```

### Mode: `provision`

```json
{
  "provisioned_dashboards": [
    {
      "uid": "string",
      "title": "string",
      "url": "string",
      "folder": "string",
      "panels": [
        {
          "title": "string",
          "type": "graph | stat | gauge | alert-list | table",
          "metric": "string (PromQL / CloudWatch / etc.)",
          "description": "string"
        }
      ]
    }
  ],
  "provisioned_alerts": [
    {
      "uid": "string",
      "title": "string",
      "condition": "string",
      "severity": "P0 | P1 | P2 | P3",
      "notification_channels": ["string"],
      "runbook_link": "string (Confluence runbook page URL)",
      "dashboard_link": "string (panel URL for context)"
    }
  ],
  "summary": "string"
}
```

### Mode: `refresh`

Same as `baseline` output but includes a `changes_since_last` section:

```json
{
  "changes_since_last": {
    "last_baseline_date": "ISO date",
    "traffic_trend": "increasing | stable | decreasing",
    "percent_change": "number",
    "new_anomalies": ["string (description of new patterns)"],
    "alert_adjustments_recommended": [
      {
        "alert": "string (alert title)",
        "current_threshold": "string",
        "recommended_threshold": "string",
        "reason": "string"
      }
    ]
  }
}
```

### Mode: `query`

```json
{
  "query_results": [
    {
      "service": "string",
      "metrics": {
        "current_rps": "number",
        "current_latency_p99_ms": "number",
        "current_error_rate_percent": "number",
        "current_queue_depth": "number (if applicable)"
      },
      "status": "healthy | degraded | critical",
      "active_alerts": [
        {
          "title": "string",
          "state": "alerting | pending",
          "since": "ISO date",
          "dashboard_url": "string"
        }
      ],
      "recent_anomalies": [
        {
          "description": "string",
          "detected_at": "ISO date",
          "severity": "string"
        }
      ]
    }
  ]
}
```

---

## Behavior

### Mode: `baseline` — Pull Traffic Baselines

For each service specified:

1. **Discover existing dashboards** via Grafana Search API (`GET /api/search?query=[service_name]`)
2. **Discover existing alert rules** via Grafana Alerting API (`GET /api/v1/provisioning/alert-rules`)
3. **Query traffic metrics** from the appropriate datasource:
   - Prometheus: `rate(http_requests_total{service="[name]"}[5m])`
   - CloudWatch: `AWS/ApplicationELB` metrics with `TargetGroup` dimension
   - Datadog: `sum:trace.http.request.hits{service:[name]}.as_rate()`
   - Custom: attempt auto-discovery from existing dashboard panels
4. **Query latency metrics:**
   - Prometheus: `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{service="[name]"}[5m]))`
   - Adapt query syntax to match the datasource type found
5. **Query error metrics:**
   - Prometheus: `rate(http_requests_total{service="[name]",status=~"5.."}[5m]) / rate(http_requests_total{service="[name]"}[5m])`
6. **Build traffic profile** from the time series data:
   - Calculate hourly averages for daily pattern
   - Calculate daily averages for weekly pattern
   - Identify peak times and minimum times
   - Classify traffic pattern (steady, bursty, time-of-day, event-driven)
7. **Cache the baseline** for use in `validate` and `provision` modes

**Grafana API calls used:**
```
GET /api/search?query={service_name}&type=dash-db
GET /api/dashboards/uid/{uid}
GET /api/v1/provisioning/alert-rules
GET /api/ds/query  (with datasource-specific queries)
GET /api/datasources
```

### Mode: `validate` — Check PRD Estimates Against Reality

For each PRD traffic estimate:

1. Pull baselines (or use cached baselines from `baseline` mode)
2. Compare each PRD estimate against the corresponding Grafana metric:

| PRD Field | Grafana Comparison | Verdict Logic |
|-----------|-------------------|---------------|
| `launch_rps` | Current avg_rps for the service | If PRD < 50% of current → "pessimistic"; if PRD > 200% of current → "optimistic" |
| `steady_state_rps` | 7-day avg_rps | If within ±30% → "aligned"; otherwise flag deviation |
| `peak_rps` | 7-day p99_rps | If PRD < actual p99 → "pessimistic — service already exceeds this" |
| `polling_interval` | Request cadence patterns | Check if interval matches observed request patterns |
| `traffic_pattern` | Daily/weekly pattern classification | Compare classification |

3. Generate recommendations for each misaligned estimate
4. Flag services with no Grafana data as "missing baselines"

### Mode: `provision` — Create Dashboards & Alerts

From Build Brief Section 6 (Throughput SLOs) and Section 4 (traffic-based failure modes):

**Step 1: Generate Dashboard**

Create a Grafana dashboard via the Dashboard API (`POST /api/dashboards/db`) with these panels:

| Panel | Type | Metric | Purpose |
|-------|------|--------|---------|
| Request Rate (RPS) | Time series | `rate(http_requests_total{service="[name]"}[5m])` | Primary traffic signal |
| Request Rate by Status Code | Time series (stacked) | `rate(http_requests_total{service="[name]"}[5m]) by status_code` | Error breakdown |
| Latency Percentiles | Time series | `histogram_quantile([0.5,0.95,0.99], ...)` | Latency SLO tracking |
| Error Rate (%) | Stat | `5xx / total × 100` | Error SLO tracking |
| Throughput vs Baseline | Time series (with threshold bands) | Current RPS overlaid with ±threshold from baseline | Anomaly visualization |
| Queue Depth (if applicable) | Time series | Queue-specific metric | Backpressure signal |
| Traffic Anomaly Detection | Alert list | Alerts from traffic-based rules | Quick anomaly view |
| SLO Burn Rate | Gauge | Error budget consumption rate | SLO health |

**Step 2: Generate Alert Rules**

Create alert rules via Grafana Alerting API (`POST /api/v1/provisioning/alert-rules`) from the Build Brief:

| Build Brief Source | Alert Rule |
|-------------------|------------|
| Steady-state RPS SLO | `avg(rate(http_requests_total[5m])) < [threshold]` for > 5 min → P1 |
| Peak RPS capacity SLO | `avg(rate(http_requests_total[1m])) > [threshold]` for > 1 min → P2 |
| Traffic anomaly detection | `abs(current_rps - baseline_rps) / baseline_rps > [threshold]` → P2 |
| Zero-traffic detection | `rate(http_requests_total[1m]) == 0` during business hours → P0 |
| RPS drop > 50% | `rate(http_requests_total[5m]) < 0.5 * baseline_avg` for > 2 min → P1 |
| RPS spike > 3x | `rate(http_requests_total[1m]) > 3 * baseline_avg` for > 1 min → P1 |
| Gradual RPS decline | Hourly comparison showing consistent 10%+ decline → P2 |

Each alert rule includes:
- `runbook_link` annotation pointing to the Confluence runbook
- `dashboard_link` annotation pointing to the relevant dashboard panel
- Notification channel from `output_config`

**Step 3: Link to Incident Runbook**

Output dashboard URLs and alert rule UIDs so the Incident Runbook Skill can embed direct links:
- Each failure mode in the runbook gets a "Dashboard" link to the relevant Grafana panel
- Each SLO in the runbook gets a "Dashboard" link to the SLO burn rate panel

### Mode: `refresh` — Update Baselines

1. Pull new baselines using `baseline` mode
2. Compare against the last cached baseline
3. Identify trends (increasing, stable, decreasing traffic)
4. Flag if existing alert thresholds are now misaligned with actual traffic
5. Recommend alert adjustments

**Trigger for automated refresh:** Can be scheduled (weekly) or triggered when a deploy changes the service's behavior. The Build Brief's CI/CD pipeline can include a post-deploy step that refreshes baselines.

### Mode: `query` — Real-Time Service Status

Used during incident response or on-demand investigation:

1. Query current metrics (last 5 minutes)
2. Check active alert states
3. Compare current metrics against cached baselines
4. Flag anomalies
5. Return a quick health assessment

---

## Datasource Auto-Detection

The skill auto-detects the Grafana datasource type and adapts queries:

| Datasource Type | Detection | Query Adaptation |
|----------------|-----------|-----------------|
| Prometheus | `type: "prometheus"` in datasource config | PromQL queries |
| CloudWatch | `type: "cloudwatch"` | CloudWatch Metrics Insights queries |
| InfluxDB | `type: "influxdb"` | Flux or InfluxQL queries |
| Elasticsearch | `type: "elasticsearch"` | Lucene queries with date histogram |
| Datadog | `type: "datadog"` (via plugin) | Datadog metric queries |
| Google Cloud Monitoring | `type: "stackdriver"` | MQL queries |

If the datasource is unknown or custom, the skill:
1. Examines existing dashboard panels for the service to discover working queries
2. Reuses discovered query patterns with modified parameters
3. Falls back to generic metric names (`http_requests_total`, `request_duration_seconds`)

---

## MCP Server Contract

### Tool: `grafana_baselines`

```json
{
  "name": "grafana_baselines",
  "description": "Pull traffic baselines, latency profiles, and existing observability state from Grafana for specified services",
  "inputSchema": {
    "type": "object",
    "properties": {
      "services": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "name": {"type": "string"},
            "namespace": {"type": "string"}
          },
          "required": ["name"]
        },
        "description": "Services to pull baselines for"
      },
      "time_range_days": {
        "type": "number",
        "default": 7,
        "description": "Number of days to look back for baselines"
      },
      "include_dashboards": {
        "type": "boolean",
        "default": true,
        "description": "Include existing dashboard inventory"
      },
      "include_alerts": {
        "type": "boolean",
        "default": true,
        "description": "Include existing alert rule inventory"
      }
    },
    "required": ["services"]
  }
}
```

### Tool: `grafana_validate_estimates`

```json
{
  "name": "grafana_validate_estimates",
  "description": "Validate PRD traffic estimates against actual Grafana metrics",
  "inputSchema": {
    "type": "object",
    "properties": {
      "services": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "name": {"type": "string"},
            "namespace": {"type": "string"}
          },
          "required": ["name"]
        }
      },
      "prd_estimates": {
        "type": "object",
        "properties": {
          "launch_rps": {"type": "number"},
          "steady_state_rps": {"type": "number"},
          "peak_rps": {"type": "number"},
          "polling_interval_seconds": {"type": "number"},
          "traffic_pattern": {"type": "string"}
        },
        "description": "Traffic estimates from the PRD"
      }
    },
    "required": ["services", "prd_estimates"]
  }
}
```

### Tool: `grafana_provision`

```json
{
  "name": "grafana_provision",
  "description": "Provision Grafana dashboards and alert rules from Build Brief throughput SLOs and failure modes",
  "inputSchema": {
    "type": "object",
    "properties": {
      "build_brief": {
        "type": "string",
        "description": "Build Brief markdown — Section 6 (SLOs) and Section 4 (failure modes) are consumed"
      },
      "service_name": {
        "type": "string",
        "description": "Primary service name for the feature"
      },
      "dashboard_folder": {
        "type": "string",
        "default": "ADLC Features",
        "description": "Grafana folder to create dashboards in"
      },
      "notification_channel": {
        "type": "string",
        "description": "Notification channel for alert rules (Slack channel, PagerDuty service, etc.)"
      },
      "runbook_url": {
        "type": "string",
        "description": "Confluence runbook URL to link in alert annotations"
      },
      "alert_format": {
        "type": "string",
        "enum": ["grafana_native", "prometheus_rules", "both"],
        "default": "grafana_native"
      }
    },
    "required": ["build_brief", "service_name"]
  }
}
```

### Tool: `grafana_query`

```json
{
  "name": "grafana_query",
  "description": "Query current metrics and health status for a service from Grafana. Used for incident response, on-demand investigation, or real-time status checks.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "service_name": {
        "type": "string",
        "description": "Service to query"
      },
      "namespace": {
        "type": "string",
        "description": "Optional Kubernetes namespace or environment"
      },
      "time_range_minutes": {
        "type": "number",
        "default": 5,
        "description": "How far back to look (default: 5 minutes for real-time)"
      },
      "include_alerts": {
        "type": "boolean",
        "default": true,
        "description": "Include active alert states"
      },
      "compare_to_baseline": {
        "type": "boolean",
        "default": true,
        "description": "Compare current metrics against cached baselines"
      }
    },
    "required": ["service_name"]
  }
}
```

### Tool: `grafana_refresh_baselines`

```json
{
  "name": "grafana_refresh_baselines",
  "description": "Refresh cached traffic baselines and recommend alert threshold adjustments",
  "inputSchema": {
    "type": "object",
    "properties": {
      "services": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "name": {"type": "string"},
            "namespace": {"type": "string"}
          },
          "required": ["name"]
        }
      },
      "time_range_days": {
        "type": "number",
        "default": 7,
        "description": "Number of days for new baseline window"
      },
      "auto_adjust_alerts": {
        "type": "boolean",
        "default": false,
        "description": "If true, automatically update alert thresholds (requires Editor role). If false, only recommend adjustments."
      }
    },
    "required": ["services"]
  }
}
```

---

## CLI Interface

```bash
# Pull traffic baselines for a service
adlc-grafana baselines --service api-server --days 7

# Pull baselines for multiple services
adlc-grafana baselines --services api-server,worker,auth-service --days 14

# Validate PRD traffic estimates against Grafana
adlc-grafana validate --service api-server --prd ./prd.md

# Provision dashboards and alerts from Build Brief
adlc-grafana provision --brief ./build-brief.md --service widget-service --folder "ADLC Features" --notify "#eng-alerts"

# Query real-time service status
adlc-grafana query --service api-server --minutes 5

# Refresh baselines and check for alert drift
adlc-grafana refresh --service api-server --days 7

# Refresh and auto-adjust alert thresholds
adlc-grafana refresh --service api-server --days 7 --auto-adjust
```

---

## Grafana API Authentication

The skill requires a Grafana Service Account token with appropriate permissions:

| Mode | Minimum Role | Why |
|------|-------------|-----|
| `baseline` | Viewer | Read dashboards, datasources, and query metrics |
| `validate` | Viewer | Read metrics for comparison |
| `provision` | Editor | Create dashboards and alert rules |
| `refresh` (read-only) | Viewer | Read metrics for comparison |
| `refresh` (auto-adjust) | Editor | Update alert rule thresholds |
| `query` | Viewer | Read current metrics and alert states |

**Setup:**
1. Create a Grafana Service Account (Admin → Service Accounts)
2. Assign the appropriate role (Viewer for read-only, Editor for provisioning)
3. Generate a Service Account Token
4. Provide the token via MCP server configuration or environment variable (`GRAFANA_API_TOKEN`)

---

## Downstream Consumers

| Consumer | What They Use | How |
|----------|-------------|-----|
| **Build Brief Agent (Phase 6)** | `baseline` output → pre-fills throughput SLOs with real data | Traffic baselines replace PRD estimates where available |
| **Build Brief Agent (Phase 4)** | `baseline` output → informs traffic-based failure detection thresholds | Real baselines make anomaly detection accurate |
| **Eval Council** | `validate` output → validates that throughput SLOs are realistic | Flags SLOs that conflict with Grafana reality |
| **Incident Runbook Skill** | `provision` output → dashboard URLs and alert rule links | Runbook includes direct links to Grafana panels |
| **Slack Orchestration Skill** | `query` output → real-time service status during incidents | Posts Grafana status to Slack channels |
| **CI/CD Pipeline Skill** | `provision` output → post-deploy baseline refresh trigger | Pipeline triggers `refresh` after deploy |
| **Engineer (directly)** | All modes → traffic context for architecture and capacity decisions | Engineer sees real data, not guesses |

---

## Long-Term Capabilities (Roadmap)

These capabilities are not in v1 but the skill architecture supports them:

### Automated Anomaly Detection
- Schedule `refresh` mode on a recurring basis (e.g., weekly)
- Compare new baselines against historical baselines
- Auto-generate anomaly alerts when traffic patterns shift significantly
- Feed anomaly data into the Incident Runbook Skill to trigger proactive investigations

### Cross-Service Traffic Correlation
- Pull baselines for all services in a dependency chain
- Detect when upstream traffic changes cascade to downstream services
- Generate correlation dashboards showing request flow across services
- Alert when a traffic pattern in Service A should propagate to Service B but doesn't (indicating a failure)

### Capacity Planning Triggers
- Track traffic growth trends over time
- Alert when a service approaches its throughput ceiling (based on load test results or historical peak data)
- Feed capacity data into the Build Brief's infrastructure sizing decisions
- Recommend scaling actions before traffic exceeds capacity

### SLO Lifecycle Management
- Track SLO burn rates over time
- Recommend SLO target adjustments based on actual performance
- Alert when SLO targets become unrealistic (either too loose or too tight)
- Generate SLO status reports for engineering reviews

### Alert Fatigue Reduction
- Track alert firing frequency and resolution patterns
- Identify noisy alerts (high fire rate, low action rate)
- Recommend alert consolidation or threshold adjustments
- Generate alert health reports

---

## Quality Gates

- [ ] Every service specified in the input produces a baseline (or an explicit "no data" finding with reason)
- [ ] Traffic baselines include daily and weekly patterns (not just flat averages)
- [ ] Validation results include a verdict for every PRD estimate provided
- [ ] Provisioned dashboards are accessible via the returned URL
- [ ] Provisioned alert rules are active and correctly configured (test with a dry-run where possible)
- [ ] Alert rules include `runbook_link` and `dashboard_link` annotations
- [ ] Datasource auto-detection correctly identifies the query language for the service's metrics
- [ ] Cached baselines are invalidated and refreshed when requested
- [ ] No Grafana API credentials are logged or included in output
- [ ] Provisioned resources follow Grafana folder and naming conventions
- [ ] All Grafana API calls handle rate limiting, authentication errors, and network failures gracefully
- [ ] Output JSON is parseable by downstream skills (Incident Runbook, Eval Council, Slack Orchestration)

## Framework Hardening Addendum

- **Contract versioning:** Baseline/provision/check APIs include `contract_version` and compatibility enforcement.
- **Schema validation:** Validate throughput SLO and alert configuration inputs against declared contract fields before provisioning.
- **Idempotency:** Dashboard and alert provisioning must dedupe by stable UID/idempotency key across retries.
- **Structured errors:** Return typed failures for auth, datasource, contract mismatch, and permission errors with stop reason mapping.

