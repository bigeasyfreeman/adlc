# Skill: Helm & ArgoCD Deployment

> Validates Helm charts and generates ArgoCD Application manifests when the ADLC pipeline produces infrastructure or service code. Ensures every deployable artifact has correct chart structure, environment-specific values, and a GitOps-ready Application manifest before code review.

---

## Why This Exists

Without deployment validation in the pipeline, common failures slip through to production:
- **Helm charts fail `helm template`** because of missing values, broken Go templates, or incompatible dependency versions
- **ArgoCD Applications point at stale refs** — wrong targetRevision, mismatched repoURL, or orphaned Application manifests
- **Environment drift** — dev values leak into prod, resource limits are missing, health probes are absent
- **Anti-patterns accumulate** — hardcoded image tags, secrets in plain text, missing labels, no pod disruption budgets
- **Multi-cluster rollouts are ad-hoc** — no consistent Application-per-environment pattern, no sync policy conventions

This skill bridges the gap between "code that builds" and "code that deploys correctly." It runs at two points in the pipeline:

1. **Scaffold phase:** When a new service or infrastructure component is created, generates the Helm chart skeleton and ArgoCD Application manifests
2. **QA / PR-prep phase:** Validates existing Helm charts against best practices and ensures ArgoCD manifests are consistent with the target environments

---

## Trigger

| When | What | Mode |
|------|------|------|
| Coder agent produces Helm charts or K8s manifests | Validate chart structure, template rendering, and best practices | `validate` |
| New service is scaffolded (scaffold DAG node) | Generate Helm chart skeleton and ArgoCD Application manifests | `generate` |
| PR preparation phase | Cross-check deployment configs against environment targets and Build Brief infra tasks | `audit` |
| On-demand | Validate a specific chart or generate manifests for an existing service | `validate` or `generate` |

---

## Input Contract

```json
{
  "contract_version": "1.0.0",
  "mode": "validate | generate | audit",
  "repo_path": "string (path to repository root)",
  "chart_paths": [
    "string (relative path to Helm chart directories — e.g., 'charts/my-app', 'deploy/helm')"
  ],
  "service_name": "string (service name for generation mode — e.g., 'my-app')",
  "environments": [
    {
      "name": "string (e.g., 'dev', 'staging', 'prod')",
      "cluster": "string (cluster name or URL — e.g., 'dev-cluster', 'prod-cluster')",
      "namespace": "string (target namespace — e.g., 'team-namespace')",
      "values_overrides": {
        "replicas": "number (optional)",
        "resources": "object (optional — CPU/memory limits)",
        "image_tag_strategy": "string (optional — 'branch-sha' | 'semver' | 'latest')"
      }
    }
  ],
  "argocd_config": {
    "repo_url": "string (Git repository URL for ArgoCD source)",
    "target_revision": "string (branch or tag — e.g., 'main', 'HEAD', 'v1.2.3')",
    "project": "string (ArgoCD project — e.g., 'default', 'team-project')",
    "sync_policy": "auto | manual | auto_prune",
    "application_path": "string (directory for ArgoCD Application manifests — e.g., 'argocd/applications')"
  },
  "build_brief_infra_tasks": [
    {
      "task_id": "string",
      "description": "string",
      "deployment_target": "kubernetes",
      "acceptance_criteria": ["string"]
    }
  ],
  "validation_config": {
    "strict_mode": "boolean (default: true — fail on warnings)",
    "kubernetes_version": "string (optional — e.g., '1.29' — for API deprecation checks)",
    "additional_lint_rules": ["string (optional — custom OPA/Rego policies or kube-linter rules)"]
  }
}
```

---

## Output Contract

### Mode: `validate`

```json
{
  "contract_version": "1.0.0",
  "mode": "validate",
  "charts_validated": [
    {
      "chart_path": "string",
      "chart_name": "string",
      "chart_version": "string",
      "app_version": "string",
      "template_render": {
        "status": "pass | fail",
        "errors": ["string"],
        "warnings": ["string"],
        "rendered_resource_count": "number"
      },
      "lint_result": {
        "status": "pass | fail",
        "errors": ["string"],
        "warnings": ["string"]
      },
      "values_schema_validation": {
        "status": "pass | fail | no_schema",
        "missing_required_values": ["string"],
        "type_mismatches": ["string"]
      },
      "dependency_check": {
        "status": "pass | fail | no_dependencies",
        "outdated_dependencies": [
          {
            "name": "string",
            "current_version": "string",
            "latest_version": "string",
            "breaking_changes": "boolean"
          }
        ],
        "missing_dependencies": ["string"]
      },
      "anti_pattern_findings": [
        {
          "rule": "string (e.g., 'hardcoded-image-tag', 'missing-resource-limits')",
          "severity": "error | warning | info",
          "file": "string",
          "line": "number (if applicable)",
          "message": "string",
          "fix_suggestion": "string"
        }
      ],
      "environment_checks": [
        {
          "environment": "string",
          "values_file_exists": "boolean",
          "resource_limits_set": "boolean",
          "health_probes_defined": "boolean",
          "replica_count_appropriate": "boolean",
          "findings": ["string"]
        }
      ]
    }
  ],
  "overall_status": "pass | fail | warn",
  "summary": "string",
  "generated_at": "ISO date"
}
```

### Mode: `generate`

```json
{
  "contract_version": "1.0.0",
  "mode": "generate",
  "generated_chart": {
    "chart_path": "string",
    "files_created": [
      {
        "path": "string",
        "description": "string"
      }
    ],
    "chart_name": "string",
    "chart_version": "string"
  },
  "generated_argocd_applications": [
    {
      "environment": "string",
      "file_path": "string",
      "application_name": "string",
      "destination_cluster": "string",
      "destination_namespace": "string",
      "sync_policy": "string"
    }
  ],
  "generated_values_overlays": [
    {
      "environment": "string",
      "file_path": "string",
      "description": "string"
    }
  ],
  "summary": "string",
  "generated_at": "ISO date"
}
```

### Mode: `audit`

```json
{
  "contract_version": "1.0.0",
  "mode": "audit",
  "deployment_readiness": {
    "status": "ready | not_ready | needs_review",
    "checklist": [
      {
        "check": "string",
        "status": "pass | fail | skip",
        "detail": "string"
      }
    ]
  },
  "environment_consistency": [
    {
      "environment": "string",
      "argocd_application_exists": "boolean",
      "values_file_exists": "boolean",
      "sync_policy_matches_convention": "boolean",
      "drift_detected": "boolean",
      "findings": ["string"]
    }
  ],
  "cross_reference_results": [
    {
      "build_brief_task_id": "string",
      "deployment_artifact_found": "boolean",
      "detail": "string"
    }
  ],
  "summary": "string",
  "generated_at": "ISO date"
}
```

---

## Behavior

### Mode: `validate` — Helm Chart Validation

For each chart path specified:

**Step 1: Chart Structure Check**

Verify the chart directory contains required files:
```
Chart.yaml          — must exist, valid YAML, apiVersion v2
values.yaml         — must exist, non-empty
templates/          — must exist, contains at least one template
templates/NOTES.txt — recommended
.helmignore         — recommended
```

**Step 2: Template Rendering**

Run `helm template` with each environment's values file to catch rendering errors:
```bash
# Render with default values
helm template [release-name] [chart-path]

# Render with each environment overlay
helm template [release-name] [chart-path] -f values.yaml -f values-dev.yaml
helm template [release-name] [chart-path] -f values.yaml -f values-staging.yaml
helm template [release-name] [chart-path] -f values.yaml -f values-prod.yaml
```

Capture and categorize all errors and warnings.

**Step 3: Lint**

Run `helm lint` for syntax and best-practice checks:
```bash
helm lint [chart-path] --strict
helm lint [chart-path] -f values-prod.yaml --strict
```

**Step 4: Values Schema Validation**

If `values.schema.json` exists:
- Validate each values file against the schema
- Report missing required values
- Report type mismatches

If no schema exists, flag as `info` recommendation to add one.

**Step 5: Dependency Check**

If `Chart.yaml` declares dependencies:
```bash
helm dependency list [chart-path]
helm dependency build [chart-path]
```
- Check for outdated sub-chart versions
- Verify dependency repositories are reachable
- Flag incompatible version constraints

**Step 6: Anti-Pattern Detection**

Scan templates and values for common issues:

| Rule ID | Description | Severity | Check |
|---------|-------------|----------|-------|
| `hardcoded-image-tag` | Image tag is hardcoded (not templated) | error | Scan for `image:` without `{{ }}` |
| `missing-resource-limits` | Pod spec lacks resource requests/limits | error | Check Deployment/StatefulSet specs |
| `no-health-probes` | No readiness/liveness probes defined | error | Check pod template spec |
| `no-pod-disruption-budget` | No PodDisruptionBudget for production | warning | Check for PDB template |
| `secrets-in-values` | Plain-text secrets in values.yaml | error | Pattern-match for passwords, tokens, keys |
| `missing-labels` | Standard labels (app, version, component) missing | warning | Check metadata.labels |
| `no-service-account` | Pod runs without explicit ServiceAccount | warning | Check serviceAccountName |
| `host-network-enabled` | hostNetwork: true without justification | error | Check pod spec |
| `privileged-container` | Runs in privileged mode | error | Check securityContext |
| `latest-tag` | Image uses `latest` tag | error | Check image references |
| `no-network-policy` | No NetworkPolicy defined | info | Check for NetworkPolicy template |
| `missing-annotations` | No common annotations (prometheus scrape, etc.) | info | Check metadata.annotations |

**Step 7: Environment-Specific Checks**

For each target environment:
- Verify environment-specific values file exists
- Check resource limits are set (required for staging/prod)
- Verify health probes are defined
- Check replica count is appropriate for the environment
- Verify image pull policy matches environment conventions

### Mode: `generate` — Scaffold Chart & ArgoCD Manifests

**Step 1: Generate Helm Chart Skeleton**

Create a new chart at the specified path:

```
charts/[service-name]/
├── Chart.yaml
├── values.yaml
├── values-dev.yaml
├── values-staging.yaml
├── values-prod.yaml
├── values.schema.json
├── .helmignore
└── templates/
    ├── NOTES.txt
    ├── _helpers.tpl
    ├── deployment.yaml
    ├── service.yaml
    ├── serviceaccount.yaml
    ├── hpa.yaml
    ├── pdb.yaml
    ├── ingress.yaml
    ├── configmap.yaml
    └── networkpolicy.yaml
```

**Chart.yaml template:**
```yaml
apiVersion: v2
name: {{ service_name }}
description: A Helm chart for {{ service_name }}
type: application
version: 0.1.0
appVersion: "0.1.0"
maintainers:
  - name: {{ owner }}
```

**values.yaml template (base):**
```yaml
replicaCount: 1

image:
  repository: "registry.example.com/{{ service_name }}"
  pullPolicy: IfNotPresent
  tag: ""  # Overridden by CI/CD

serviceAccount:
  create: true
  name: ""
  annotations: {}

service:
  type: ClusterIP
  port: 80
  targetPort: 8080

ingress:
  enabled: false
  className: ""
  annotations: {}
  hosts:
    - host: "{{ service_name }}.example.com"
      paths:
        - path: /
          pathType: Prefix
  tls: []

resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 256Mi

livenessProbe:
  httpGet:
    path: /healthz
    port: http
  initialDelaySeconds: 15
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /readyz
    port: http
  initialDelaySeconds: 5
  periodSeconds: 5

autoscaling:
  enabled: false
  minReplicas: 1
  maxReplicas: 10
  targetCPUUtilizationPercentage: 80

podDisruptionBudget:
  enabled: false
  minAvailable: 1

networkPolicy:
  enabled: false

nodeSelector: {}
tolerations: []
affinity: {}
```

**Environment overlay template (values-prod.yaml):**
```yaml
replicaCount: 3

resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: "1"
    memory: 1Gi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70

podDisruptionBudget:
  enabled: true
  minAvailable: 2

networkPolicy:
  enabled: true
```

**Step 2: Generate ArgoCD Application Manifests**

For each target environment, generate an Application manifest:

```yaml
# argocd/applications/[service-name]-[env].yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: {{ service_name }}-{{ environment }}
  namespace: argocd
  labels:
    app.kubernetes.io/name: {{ service_name }}
    app.kubernetes.io/instance: {{ service_name }}-{{ environment }}
    app.kubernetes.io/managed-by: argocd
    environment: {{ environment }}
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: {{ argocd_project }}
  source:
    repoURL: {{ repo_url }}
    targetRevision: {{ target_revision }}
    path: charts/{{ service_name }}
    helm:
      valueFiles:
        - values.yaml
        - values-{{ environment }}.yaml
  destination:
    server: {{ cluster_url }}
    namespace: {{ namespace }}
  syncPolicy:
    # auto-sync for dev/staging, manual for prod
    automated:  # Remove this block for prod if manual sync preferred
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
      - PrunePropagationPolicy=foreground
    retry:
      limit: 3
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers:
        - /spec/replicas  # Ignore if HPA manages replicas
```

**Sync policy conventions:**

| Environment | Sync Policy | Prune | Self-Heal | Rationale |
|-------------|------------|-------|-----------|-----------|
| dev | automated | true | true | Fast iteration, auto-cleanup |
| staging | automated | true | true | Mirror prod behavior automatically |
| prod | manual or automated | true | true | Automated with optional manual gate |

**Step 3: Generate ApplicationSet (if multi-cluster)**

If more than two environments are specified, generate an ApplicationSet for DRY multi-cluster deployment:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: {{ service_name }}
  namespace: argocd
spec:
  generators:
    - list:
        elements:
          - env: dev
            cluster: dev-cluster
            namespace: team-namespace
            values_file: values-dev.yaml
          - env: staging
            cluster: staging-cluster
            namespace: team-namespace
            values_file: values-staging.yaml
          - env: prod
            cluster: prod-cluster
            namespace: team-namespace
            values_file: values-prod.yaml
  template:
    metadata:
      name: "{{ service_name }}-{{`{{env}}`}}"
      namespace: argocd
    spec:
      project: {{ argocd_project }}
      source:
        repoURL: {{ repo_url }}
        targetRevision: {{ target_revision }}
        path: charts/{{ service_name }}
        helm:
          valueFiles:
            - values.yaml
            - "{{`{{values_file}}`}}"
      destination:
        server: "{{`{{cluster}}`}}"
        namespace: "{{`{{namespace}}`}}"
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

### Mode: `audit` — Deployment Readiness Check

Cross-reference deployment artifacts against Build Brief infra tasks and environment conventions.

**Step 1: Deployment Readiness Checklist**

| # | Check | Required For |
|---|-------|-------------|
| 1 | Helm chart passes `helm lint --strict` | All |
| 2 | Helm chart renders successfully with each env values file | All |
| 3 | ArgoCD Application manifest exists for each target environment | All |
| 4 | ArgoCD Application references correct repo URL and revision | All |
| 5 | Values files exist for all target environments | All |
| 6 | Resource limits are defined in staging and prod values | Staging, Prod |
| 7 | Health probes (liveness + readiness) are defined | All |
| 8 | PodDisruptionBudget is defined for prod | Prod |
| 9 | NetworkPolicy is defined for prod | Prod |
| 10 | No hardcoded image tags in templates | All |
| 11 | No plain-text secrets in values files | All |
| 12 | HPA is configured or replica count is set appropriately | Staging, Prod |
| 13 | Sync policy matches environment convention | All |
| 14 | Ingress/Gateway config is consistent across environments | All (if applicable) |
| 15 | Chart version has been bumped if templates changed | All |

**Step 2: Environment Consistency Check**

For each target environment:
- Verify ArgoCD Application manifest exists and points to correct chart path
- Verify values overlay file exists and contains environment-appropriate settings
- Check sync policy matches convention (auto for dev/staging, manual or auto for prod)
- Detect drift between Application manifest and actual chart directory structure

**Step 3: Build Brief Cross-Reference**

For each infra task in the Build Brief:
- Check that a corresponding deployment artifact exists (Helm chart, ArgoCD Application, values overlay)
- Flag tasks that mention deployment but have no matching artifacts
- Flag artifacts that exist but are not referenced in any Build Brief task

---

## Anti-Pattern Catalog

The skill maintains a catalog of Helm and Kubernetes anti-patterns with automated detection:

### Helm Anti-Patterns

| ID | Pattern | Detection | Fix |
|----|---------|-----------|-----|
| H-001 | Hardcoded image tags | Regex scan for `image: .*:(?!{{)` in templates | Use `{{ .Values.image.tag }}` |
| H-002 | No values.schema.json | File existence check | Generate schema from values.yaml |
| H-003 | Unused values | Cross-reference values.yaml keys against template usage | Remove or document unused values |
| H-004 | Nested chart version pinned to `*` | Parse Chart.yaml dependencies | Pin to specific version ranges |
| H-005 | No NOTES.txt | File existence check | Generate connection instructions |
| H-006 | Duplicate template logic | AST comparison across templates | Extract to _helpers.tpl |
| H-007 | Missing `helm.sh/chart` label | Label check on all resources | Add standard Helm labels |

### Kubernetes Anti-Patterns

| ID | Pattern | Detection | Fix |
|----|---------|-----------|-----|
| K-001 | No resource limits | Render templates, check pod specs | Add requests and limits |
| K-002 | No health probes | Check pod spec for liveness/readiness | Add appropriate probes |
| K-003 | Running as root | Check securityContext | Set `runAsNonRoot: true` |
| K-004 | No PDB for replicated workloads | Check Deployment replicas vs PDB existence | Add PodDisruptionBudget |
| K-005 | Secrets in environment variables | Check env/envFrom for Secret refs vs plain values | Use Secret references or external secrets |
| K-006 | No anti-affinity for replicated pods | Check pod affinity rules | Add pod anti-affinity |
| K-007 | Missing `app.kubernetes.io/*` labels | Check metadata.labels | Add standard labels |
| K-008 | No ServiceAccount | Check serviceAccountName in pod spec | Create and reference ServiceAccount |
| K-009 | Using deprecated APIs | Compare apiVersion against target K8s version | Migrate to current API version |
| K-010 | No topology spread constraints | Check pod topology constraints for multi-AZ | Add topology spread for HA |

### ArgoCD Anti-Patterns

| ID | Pattern | Detection | Fix |
|----|---------|-----------|-----|
| A-001 | No sync policy defined | Parse Application spec | Add appropriate sync policy |
| A-002 | Auto-sync on prod without review gate | Check prod Application sync config | Add manual sync or approval workflow |
| A-003 | Missing finalizers | Check Application metadata | Add `resources-finalizer.argocd.argoproj.io` |
| A-004 | Hardcoded cluster URL | Check destination.server for literals | Use cluster name or variable |
| A-005 | No retry policy | Check syncPolicy.retry | Add retry with backoff |
| A-006 | Missing ignoreDifferences for HPA-managed fields | Check for HPA + no ignoreDifferences | Add `/spec/replicas` to ignoreDifferences |
| A-007 | No resource tracking annotation | Check annotations for `argocd.argoproj.io/tracking-id` | Enable server-side diff or annotation tracking |

---

## MCP Server Contract

### Tool: `helm_validate`

```json
{
  "name": "helm_validate",
  "description": "Validate Helm charts against best practices, render templates, lint, check dependencies, and detect anti-patterns",
  "inputSchema": {
    "type": "object",
    "properties": {
      "chart_path": {
        "type": "string",
        "description": "Path to the Helm chart directory"
      },
      "values_files": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Additional values files to validate against"
      },
      "strict": {
        "type": "boolean",
        "default": true,
        "description": "Fail on warnings in addition to errors"
      },
      "kubernetes_version": {
        "type": "string",
        "description": "Target Kubernetes version for API deprecation checks (e.g., '1.29')"
      }
    },
    "required": ["chart_path"]
  }
}
```

### Tool: `helm_generate_chart`

```json
{
  "name": "helm_generate_chart",
  "description": "Generate a Helm chart skeleton with best-practice defaults, environment-specific values overlays, and values schema",
  "inputSchema": {
    "type": "object",
    "properties": {
      "service_name": {
        "type": "string",
        "description": "Name of the service (used for chart name and resource names)"
      },
      "output_path": {
        "type": "string",
        "description": "Directory to create the chart in (e.g., 'charts/')"
      },
      "environments": {
        "type": "array",
        "items": {"type": "string"},
        "default": ["dev", "staging", "prod"],
        "description": "Environments to generate values overlays for"
      },
      "include_ingress": {
        "type": "boolean",
        "default": false,
        "description": "Include ingress template"
      },
      "include_hpa": {
        "type": "boolean",
        "default": true,
        "description": "Include HorizontalPodAutoscaler template"
      },
      "include_pdb": {
        "type": "boolean",
        "default": true,
        "description": "Include PodDisruptionBudget template"
      },
      "include_network_policy": {
        "type": "boolean",
        "default": true,
        "description": "Include NetworkPolicy template"
      }
    },
    "required": ["service_name", "output_path"]
  }
}
```

### Tool: `argocd_generate_application`

```json
{
  "name": "argocd_generate_application",
  "description": "Generate ArgoCD Application or ApplicationSet manifests for multi-environment deployment",
  "inputSchema": {
    "type": "object",
    "properties": {
      "service_name": {
        "type": "string",
        "description": "Service name for the Application"
      },
      "chart_path": {
        "type": "string",
        "description": "Relative path to the Helm chart in the repo"
      },
      "repo_url": {
        "type": "string",
        "description": "Git repository URL"
      },
      "environments": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "name": {"type": "string"},
            "cluster": {"type": "string"},
            "namespace": {"type": "string"},
            "sync_policy": {
              "type": "string",
              "enum": ["auto", "manual", "auto_prune"]
            }
          },
          "required": ["name", "cluster", "namespace"]
        },
        "description": "Target environments with cluster and namespace details"
      },
      "project": {
        "type": "string",
        "default": "default",
        "description": "ArgoCD project name"
      },
      "target_revision": {
        "type": "string",
        "default": "HEAD",
        "description": "Git branch or tag for the source"
      },
      "output_path": {
        "type": "string",
        "description": "Directory to write Application manifests to"
      },
      "use_application_set": {
        "type": "boolean",
        "default": false,
        "description": "Generate an ApplicationSet instead of individual Applications"
      }
    },
    "required": ["service_name", "chart_path", "repo_url", "environments"]
  }
}
```

### Tool: `deployment_audit`

```json
{
  "name": "deployment_audit",
  "description": "Audit deployment readiness by cross-referencing Helm charts, ArgoCD Applications, and Build Brief infra tasks",
  "inputSchema": {
    "type": "object",
    "properties": {
      "repo_path": {
        "type": "string",
        "description": "Path to the repository root"
      },
      "chart_paths": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Helm chart directories to audit"
      },
      "argocd_application_paths": {
        "type": "array",
        "items": {"type": "string"},
        "description": "ArgoCD Application manifest paths to audit"
      },
      "build_brief": {
        "type": "string",
        "description": "Build Brief markdown — Section 8 (Infra tasks) is consumed"
      },
      "environments": {
        "type": "array",
        "items": {"type": "string"},
        "default": ["dev", "staging", "prod"],
        "description": "Expected target environments"
      }
    },
    "required": ["repo_path"]
  }
}
```

---

## CLI Interface

```bash
# Validate a Helm chart
adlc-deploy validate --chart ./charts/my-app

# Validate with strict mode and specific K8s version
adlc-deploy validate --chart ./charts/my-app --strict --k8s-version 1.29

# Validate with environment-specific values
adlc-deploy validate --chart ./charts/my-app -f values-prod.yaml

# Generate a new Helm chart skeleton
adlc-deploy generate-chart --service my-app --output ./charts/ --envs dev,staging,prod

# Generate ArgoCD Application manifests
adlc-deploy generate-argocd --service my-app --chart charts/my-app \
  --repo https://github.com/org/repo \
  --env dev:dev-cluster:team-namespace \
  --env staging:staging-cluster:team-namespace \
  --env prod:prod-cluster:team-namespace \
  --output ./argocd/applications/

# Generate an ApplicationSet for multi-cluster deployment
adlc-deploy generate-argocd --service my-app --chart charts/my-app \
  --repo https://github.com/org/repo \
  --env dev:dev-cluster:team-namespace \
  --env staging:staging-cluster:team-namespace \
  --env prod:prod-cluster:team-namespace \
  --output ./argocd/ --application-set

# Audit deployment readiness
adlc-deploy audit --repo . --chart charts/my-app --brief ./build-brief.md

# Full pipeline: generate + validate
adlc-deploy generate-chart --service my-app --output ./charts/ && \
adlc-deploy generate-argocd --service my-app --chart charts/my-app \
  --repo https://github.com/org/repo \
  --env dev:dev-cluster:team-namespace \
  --env prod:prod-cluster:team-namespace \
  --output ./argocd/applications/ && \
adlc-deploy validate --chart ./charts/my-app --strict
```

---

## Downstream Consumers

| Consumer | What They Use | How |
|----------|-------------|-----|
| **CI/CD Pipeline Skill** | `generate` output → chart paths and ArgoCD Application paths for pipeline wiring | CD workflows reference generated chart locations |
| **Code Reviewer Agent** | `validate` output → deployment findings in review comments | Flags anti-patterns and missing configs during code review |
| **PR Preparer Agent** | `audit` output → deployment readiness summary in PR description | PR includes deployment checklist status |
| **Incident Runbook Skill** | `generate` output → service names, namespaces, and cluster targets | Runbook includes rollback commands with correct context |
| **Grafana Observability Skill** | `generate` output → service metadata for dashboard provisioning | Dashboards are scoped to correct namespace and cluster |
| **Security Reviewer Agent** | `validate` output → security-relevant findings (privileged containers, host network, missing network policies) | Security review includes infra-level findings |
| **Eval Council** | `audit` output → validates deployment artifacts match Build Brief requirements | Council flags missing or inconsistent deployment configs |

---

## Long-Term Capabilities (Roadmap)

### Progressive Delivery Integration
- Generate Argo Rollouts with canary or blue-green strategies
- Create AnalysisTemplates that check SLO metrics during rollout
- Wire automatic rollback to error budget burn rate
- Support traffic splitting via Istio, Linkerd, or Gateway API

### Multi-Cluster Drift Detection
- Compare rendered manifests across environments to detect unintended drift
- Alert when prod and staging configs diverge beyond expected differences
- Generate drift reports as part of periodic audits

### Cost-Aware Resource Sizing
- Analyze historical resource utilization from metrics to recommend right-sized requests/limits
- Flag over-provisioned or under-provisioned environments
- Generate cost estimates for each environment's resource allocation

### Chart Dependency Supply Chain
- Track sub-chart versions against upstream releases
- Alert on known CVEs in chart dependencies
- Verify chart provenance via Helm provenance files or Sigstore signatures

### GitOps Policy Enforcement
- Integrate with OPA/Gatekeeper or Kyverno policies
- Validate rendered manifests against organizational policies before commit
- Generate policy exceptions with approval workflows

---

## Quality Gates

- [ ] Every chart path specified produces a validation report (or explicit "chart not found" with path)
- [ ] `helm template` succeeds with default values and with each environment overlay
- [ ] `helm lint --strict` passes for all charts
- [ ] Anti-pattern scan covers all templates and values files in the chart
- [ ] No `error`-severity anti-patterns remain (warnings are acceptable with justification)
- [ ] Generated ArgoCD Applications reference correct repo URL, chart path, and target revision
- [ ] Generated values overlays contain environment-appropriate defaults (prod has resource limits, PDB, network policy)
- [ ] Environment-specific values do not contain secrets in plain text
- [ ] Audit mode cross-references every Build Brief infra task against deployment artifacts
- [ ] Generated chart passes the skill's own validation mode without errors
- [ ] ArgoCD Application sync policies match environment conventions (no auto-sync on prod without explicit opt-in)
- [ ] All generated YAML is valid and parseable
- [ ] Output JSON is parseable by downstream skills (CI/CD Pipeline, Incident Runbook, Grafana Observability)
- [ ] Chart version is bumped when templates change (audit mode check)

---

## Framework Hardening Addendum

- **Contract versioning:** All input/output contracts include `contract_version` field. The skill validates incoming contract versions and rejects incompatible versions with a structured error before performing any work.
- **Schema validation:** Validate chart paths, environment configurations, and ArgoCD settings against the declared input contract schema before executing any Helm commands or generating manifests. Reject malformed inputs early with actionable error messages.
- **Idempotency:** Chart generation and ArgoCD Application creation use stable file paths derived from `service_name` + `environment` as idempotency keys. Re-running generation for the same inputs overwrites files deterministically without creating duplicates. Validation mode is inherently idempotent (read-only).
- **Structured stop reasons:** The skill emits one of the following terminal reasons on failure:
  - `chart_not_found` — specified chart path does not exist
  - `template_render_failed` — `helm template` returned non-zero exit code
  - `lint_failed` — `helm lint --strict` returned errors
  - `schema_validation_failed` — values do not conform to values.schema.json
  - `dependency_resolution_failed` — chart dependencies cannot be resolved
  - `contract_version_incompatible` — input contract version is not supported
  - `invalid_argocd_config` — ArgoCD configuration is missing required fields
  - `environment_config_missing` — required environment configuration not provided
  - `permission_denied` — insufficient filesystem permissions for generation mode
