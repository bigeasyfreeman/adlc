# Skill: Codebase Research & Repo Analysis

> Produces a structured repo map, tech debt analysis, and improvement recommendations from deep analysis of a codebase. When given a PRD, cross-references requirements against repo capabilities to identify gaps, reusable components, and prerequisite fixes. This is the first deliverable the engineer reads — not background context, but the starting point for the Build Brief conversation.

---

## Why This Exists

Every skill and agent in the ADLC system needs to understand the codebase. Without this skill, that understanding is:
- **Duplicated**: 5+ skills each scanning the same repo
- **Incomplete**: Each skill only looks for what it needs, missing cross-cutting concerns
- **Ephemeral**: Research done during the Build Brief conversation isn't available to downstream skills
- **Inconsistent**: Different skills may reach different conclusions about the same codebase

Beyond mapping, this skill **actively identifies tech debt and improvement opportunities** that affect the feature being built. The engineer should read this analysis before making any decisions.

This skill runs once, produces a canonical repo map + research deliverable, and every downstream consumer references it instead of re-discovering.

---

## Trigger

**Primary:** Activated at the very start of an ADLC workflow. The engineer provides a PRD + repo. This skill analyzes the repo and cross-references against the PRD.

**Secondary:** Can be run on-demand for any repo to produce a standalone analysis (without PRD context).

**Refresh:** Re-run when the repo has changed significantly (new service, major refactor, new framework).

---

## Input Contract

```json
{
  "repos": [
    {
      "path": "string (local path or git URL)",
      "name": "string (human-readable name)",
      "primary": true
    }
  ],
  "prd_content": "string (optional — PRD markdown for cross-referencing)",
  "focus_areas": ["string (optional — auto-detected from PRD if provided)"],
  "depth": "standard | deep",
  "exclude_paths": ["node_modules", "vendor", ".git", "dist", "build"]
}
```

When `prd_content` is provided, the skill automatically:
- Detects focus areas from the PRD (e.g., "email", "auth", "sharing", "deep linking")
- Cross-references every PRD dependency against repo capabilities
- Scopes the tech debt analysis to areas the feature touches
- Generates the PRD × Codebase cross-reference table

## Output Contract

```json
{
  "repo_map": {
    "meta": {},
    "tech_stack": {},
    "architecture": {},
    "services": [],
    "data_layer": {},
    "api_surface": {},
    "testing": {},
    "ci_cd": {},
    "observability": {},
    "security": {},
    "conventions": {},
    "dependency_graph": {},
    "risk_areas": []
  },
  "service_placement": {
    "verdict": "correct_service | wrong_service | needs_discussion",
    "reasoning": "string",
    "current_service_responsibility": "string",
    "feature_fit": "string",
    "cross_service_dependencies": [],
    "alternative_placement": "string | null"
  },
  "integration_paths": {
    "reuse": [],
    "extend": [],
    "new_required": [],
    "libraries_to_use": []
  },
  "duplication_risks": {
    "items": [],
    "scaffolding_convention": {}
  },
  "scalability": {
    "items": [],
    "async_processing": {},
    "caching": {}
  },
  "schema_intelligence": {
    "existing_models_to_reuse": [],
    "existing_patterns_to_follow": [],
    "new_models_required": [],
    "consolidation_opportunities": []
  },
  "generated_at": "ISO date",
  "repo_hash": "string (git SHA or content hash for cache invalidation)"
}
```

---

## Behavior

### 1. Meta Analysis

Establish basic facts about the repo.

```bash
# Repo size and age
git log --oneline | wc -l
git log --reverse --format="%ai" | head -1
git log -1 --format="%ai"
find . -type f | wc -l

# Language breakdown
find . -name "*.ts" -not -path "*/node_modules/*" | wc -l
find . -name "*.py" -not -path "*/venv/*" | wc -l
find . -name "*.scala" -not -path "*/target/*" | wc -l
find . -name "*.go" -not -path "*/vendor/*" | wc -l
find . -name "*.js" -not -path "*/node_modules/*" | wc -l
find . -name "*.rs" -not -path "*/target/*" | wc -l

# Monorepo detection
find . -maxdepth 2 -name "package.json" -o -name "build.sbt" -o -name "go.mod" -o -name "pyproject.toml" -o -name "Cargo.toml" | grep -v node_modules

# Active contributors (last 90 days)
git shortlog -sn --since="90 days ago" | head -10
```

**Output: `meta`**

```json
{
  "primary_language": "typescript",
  "languages": {"typescript": 420, "python": 30, "shell": 15},
  "monorepo": true,
  "packages": ["api-server", "worker", "shared-lib"],
  "total_files": 1842,
  "commits": 3201,
  "age_months": 18,
  "active_contributors": 8,
  "last_commit": "2025-01-15"
}
```

---

### 2. Tech Stack Detection

Identify frameworks, ORMs, runtimes, and key dependencies.

```bash
# Package managers and dependencies
cat package.json 2>/dev/null | head -50
cat requirements.txt 2>/dev/null || cat pyproject.toml 2>/dev/null | head -50
cat build.sbt 2>/dev/null | head -50
cat go.mod 2>/dev/null | head -30
cat Cargo.toml 2>/dev/null | head -30

# Framework detection
grep -r "express\|fastify\|koa\|nest\|hono" package.json 2>/dev/null
grep -r "flask\|django\|fastapi\|starlette" requirements.txt pyproject.toml 2>/dev/null
grep -r "akka\|http4s\|play\|zio" build.sbt 2>/dev/null

# ORM / data access
grep -r "prisma\|typeorm\|sequelize\|knex\|drizzle" package.json 2>/dev/null
grep -r "sqlalchemy\|django.db\|tortoise\|peewee" requirements.txt pyproject.toml 2>/dev/null
grep -r "doobie\|slick\|quill\|skunk" build.sbt 2>/dev/null

# Message queues / event systems
grep -r "kafka\|rabbitmq\|redis\|bull\|sqs\|pubsub\|nats" package.json requirements.txt 2>/dev/null

# Feature flags
grep -r "launchdarkly\|unleash\|flagsmith\|split\|statsig" package.json requirements.txt 2>/dev/null

# Auth
grep -r "passport\|auth0\|clerk\|supertokens\|next-auth\|lucia" package.json 2>/dev/null
```

**Output: `tech_stack`**

```json
{
  "runtime": "node 20",
  "framework": "fastify 4.x",
  "orm": "prisma 5.x",
  "database": "postgresql",
  "cache": "redis",
  "queue": "bullmq",
  "auth": "clerk",
  "feature_flags": "launchdarkly",
  "key_dependencies": [
    {"name": "zod", "purpose": "validation"},
    {"name": "pino", "purpose": "logging"},
    {"name": "opentelemetry", "purpose": "tracing"}
  ]
}
```

---

### 3. Architecture Pattern Detection

This is the most critical section. Identify how the codebase organizes domain logic, infrastructure, and boundaries.

```bash
# Directory structure (2 levels deep, excluding noise)
find . -maxdepth 3 -type d -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/dist/*" -not -path "*/build/*" | sort

# Domain / port / adapter pattern
find . -path "*/domain/*" -type f | head -20
find . -path "*/ports/*" -type f | head -20
find . -path "*/adapters/*" -type f | head -20
find . -path "*/infrastructure/*" -type f | head -20

# Interface / trait / abstract class patterns
grep -rn "export interface\|export abstract class" --include="*.ts" | head -20
grep -rn "trait.*\[F\[_\]\]\|trait.*Repository\|trait.*Service" --include="*.scala" | head -20
grep -rn "class.*ABC\|@abstractmethod" --include="*.py" | head -20
grep -rn "type.*interface" --include="*.go" | head -20

# Repository / DAO patterns
find . -name "*Repo*" -o -name "*Repository*" -o -name "*DAO*" -o -name "*repo*" | grep -v node_modules | grep -v test

# Service layer
find . -name "*Service*" -o -name "*service*" | grep -v node_modules | grep -v test | head -20

# Controller / handler / router layer
find . -name "*Controller*" -o -name "*Router*" -o -name "*Handler*" -o -name "*handler*" -o -name "*router*" | grep -v node_modules | grep -v test | head -20

# Dependency injection / wiring
grep -rn "container\|inject\|provide\|bind\|Module" --include="*.ts" --include="*.scala" --include="*.py" | grep -i "di\|inject\|container\|module" | head -10
find . -name "*module*" -o -name "*container*" -o -name "*wire*" -o -name "*inject*" | grep -v node_modules | head -10

# Error handling patterns
grep -rn "class.*Error extends\|class.*Exception\|Result<\|Either<\|Result\[" --include="*.ts" --include="*.scala" --include="*.py" | head -10
find . -name "*error*" -o -name "*exception*" | grep -v node_modules | grep -v test | head -10

# Event / messaging patterns
find . -name "*event*" -o -name "*listener*" -o -name "*subscriber*" -o -name "*publisher*" -o -name "*handler*" | grep -v node_modules | grep -v test | head -15
grep -rn "emit\|publish\|subscribe\|on(" --include="*.ts" | grep -i event | head -10

# Config management
find . -name "*.env*" -o -name "*config*" | grep -v node_modules | grep -v dist | head -15
grep -rn "process.env\|os.environ\|ConfigFactory\|viper" --include="*.ts" --include="*.py" --include="*.scala" --include="*.go" | head -10
```

**Output: `architecture`**

```json
{
  "pattern": "ports-and-adapters",
  "evidence": {
    "ports_directory": "src/domain/repos/",
    "adapters_directory": "src/server/adapters/",
    "sample_port": "src/domain/repos/CreditRepo.ts",
    "sample_adapter": "src/server/adapters/ClickHouseCreditRepo.ts"
  },
  "domain_boundary": "src/domain/ — no infrastructure imports allowed",
  "dependency_injection": {
    "mechanism": "manual wiring in src/server/container.ts",
    "pattern": "constructor injection"
  },
  "error_handling": {
    "pattern": "typed domain errors extending base DomainError",
    "location": "src/domain/errors/",
    "sample": "src/domain/errors/CreditErrors.ts"
  },
  "event_patterns": {
    "mechanism": "domain events via EventEmitter",
    "location": "src/domain/events/",
    "consumers": "src/server/listeners/"
  },
  "config_management": {
    "mechanism": "env vars loaded via dotenv, validated with zod schema",
    "location": "src/server/config.ts"
  },
  "module_boundaries": [
    {"module": "api-server", "owns": "HTTP routes, request handling", "path": "packages/api-server/"},
    {"module": "worker", "owns": "async job processing", "path": "packages/worker/"},
    {"module": "shared-lib", "owns": "domain types, shared utilities", "path": "packages/shared-lib/"}
  ],
  "conventions_summary": "Domain logic in domain/, infrastructure in server/adapters/, wired manually in container.ts. All external dependencies accessed via port interfaces. Domain layer must not import from server layer."
}
```

---

### 4. Service & Boundary Mapping

Identify discrete services, their responsibilities, and how they communicate.

```bash
# Dockerfile / service definitions
find . -name "Dockerfile*" -o -name "docker-compose*" | head -10

# Kubernetes / deployment configs
find . -name "*.yaml" -path "*/k8s/*" -o -name "*.yaml" -path "*/deploy/*" | head -10

# Service entry points
grep -rn "app.listen\|createServer\|serve\|run_app\|main" --include="*.ts" --include="*.py" --include="*.go" --include="*.scala" | grep -v test | grep -v node_modules | head -10

# Internal service communication
grep -rn "fetch\|axios\|httpClient\|grpc\|tonic" --include="*.ts" --include="*.py" --include="*.go" | grep -v test | grep -v node_modules | head -10

# Shared database usage (multiple services same DB)
grep -rn "DATABASE_URL\|connection_string\|jdbc" --include="*.env*" --include="*.ts" --include="*.py" | head -10
```

**Output: `services`**

```json
[
  {
    "name": "api-server",
    "path": "packages/api-server/",
    "entrypoint": "packages/api-server/src/index.ts",
    "port": 3000,
    "responsibility": "HTTP API, serves frontend and external clients",
    "communicates_with": ["worker (via BullMQ)", "postgresql (direct)", "redis (cache)"],
    "dockerfile": "packages/api-server/Dockerfile"
  },
  {
    "name": "worker",
    "path": "packages/worker/",
    "entrypoint": "packages/worker/src/index.ts",
    "responsibility": "Async job processing (email, reports, sync)",
    "communicates_with": ["postgresql (direct)", "redis (BullMQ)", "external APIs"],
    "dockerfile": "packages/worker/Dockerfile"
  }
]
```

---

### 5. Data Layer Analysis

Map schemas, migrations, and data access patterns.

```bash
# Migration files
find . -path "*/migrations/*" -o -path "*/migrate/*" | sort | tail -20

# Schema definitions
find . -name "schema.prisma" -o -name "*.schema.ts" -o -name "models.py" -o -name "*.entity.ts" | head -10

# Read the schema
cat prisma/schema.prisma 2>/dev/null || find . -name "schema.prisma" -exec cat {} \; 2>/dev/null | head -100

# Find all models/tables
grep -n "model\|@@map\|tableName\|__tablename__\|CREATE TABLE" prisma/schema.prisma 2>/dev/null | head -30

# Migration history
ls -la prisma/migrations/ 2>/dev/null | tail -10

# Data access patterns beyond ORM
grep -rn "raw\|rawQuery\|\$queryRaw\|execute\|sql`" --include="*.ts" --include="*.py" | grep -v test | head -10
```

**Output: `data_layer`**

```json
{
  "orm": "prisma",
  "schema_location": "prisma/schema.prisma",
  "migrations_location": "prisma/migrations/",
  "migration_count": 47,
  "last_migration": "20250110_add_widget_status",
  "models": ["User", "Account", "Widget", "Credit", "AuditLog"],
  "model_count": 12,
  "databases": [
    {"type": "postgresql", "usage": "primary data store", "connection": "DATABASE_URL"},
    {"type": "clickhouse", "usage": "analytics / read-heavy queries", "connection": "CLICKHOUSE_URL"},
    {"type": "redis", "usage": "cache + job queue", "connection": "REDIS_URL"}
  ],
  "raw_query_usage": "minimal — 3 files use $queryRaw for complex reporting queries",
  "migration_patterns": {
    "tool": "prisma migrate",
    "reversible": "manual — no auto-rollback, down migrations written by hand",
    "sample_migration": "prisma/migrations/20250110_add_widget_status/"
  }
}
```

---

### 6. API Surface Mapping

Find all exposed endpoints and their patterns.

```bash
# Route definitions
grep -rn "app.get\|app.post\|app.put\|app.delete\|app.patch\|router\." --include="*.ts" --include="*.js" | grep -v test | grep -v node_modules | head -30
grep -rn "@app.route\|@router\.\|@api\." --include="*.py" | grep -v test | head -30

# API versioning
grep -rn "/api/v[0-9]" --include="*.ts" --include="*.py" | head -10

# Middleware chain
grep -rn "app.use\|middleware\|preHandler\|beforeAll" --include="*.ts" | grep -v test | grep -v node_modules | head -15

# Request validation
grep -rn "zod\|joi\|yup\|validate\|schema" --include="*.ts" | grep -v test | grep -v node_modules | head -10

# OpenAPI / Swagger
find . -name "openapi*" -o -name "swagger*" -o -name "*.api.yaml" | head -5
```

**Output: `api_surface`**

```json
{
  "versioning": "/api/v1/",
  "total_endpoints": 34,
  "endpoint_groups": [
    {"prefix": "/api/v1/users", "methods": ["GET", "POST", "PUT"], "file": "src/server/routes/userRoutes.ts"},
    {"prefix": "/api/v1/widgets", "methods": ["GET", "POST", "PUT", "DELETE"], "file": "src/server/routes/widgetRoutes.ts"},
    {"prefix": "/api/v1/credits", "methods": ["GET"], "file": "src/server/routes/creditRoutes.ts"}
  ],
  "auth_middleware": "src/server/middleware/auth.ts — applied to all /api/ routes",
  "validation": "zod schemas co-located with route handlers",
  "openapi_spec": "docs/openapi.yaml"
}
```

---

### 7. Testing Analysis

Map test conventions, coverage, and patterns.

```bash
# Test framework config
find . -name "jest.config.*" -o -name "vitest.config.*" -o -name "pytest.ini" -o -name "conftest.py" -o -name ".mocharc.*" | head -5

# Test files
find . -name "*.test.ts" -o -name "*.spec.ts" -o -name "test_*.py" -o -name "*_test.go" -o -name "*Spec.scala" | grep -v node_modules | wc -l

# Test directory structure
find . -path "*/__tests__/*" -o -path "*/test/*" -o -path "*/tests/*" | grep -v node_modules | head -20

# Test helpers / utilities
find . -path "*/test/helpers/*" -o -path "*/test/utils/*" -o -path "*/__tests__/helpers/*" -o -path "*/test/fixtures/*" | grep -v node_modules | head -10

# Test patterns (what do tests look like)
find . -name "*.test.ts" -not -path "*/node_modules/*" | head -1 | xargs head -40 2>/dev/null

# Coverage config
grep -rn "coverage\|istanbul\|c8\|nyc" package.json jest.config.* vitest.config.* 2>/dev/null | head -5

# E2E / integration test setup
find . -name "*e2e*" -o -name "*integration*" | grep -v node_modules | head -10

# Test database setup
grep -rn "test.*database\|test.*db\|setupTests\|beforeAll\|beforeEach" --include="*.test.ts" --include="*.spec.ts" | head -10

# Mocking patterns
grep -rn "jest.mock\|vi.mock\|unittest.mock\|mockk\|when(" --include="*.test.ts" --include="*.spec.ts" --include="*.py" | head -10
```

**Output: `testing`**

```json
{
  "framework": "vitest",
  "config_file": "vitest.config.ts",
  "test_count": 342,
  "test_directory_pattern": "co-located — __tests__/ next to source files",
  "naming_convention": "*.test.ts",
  "helpers_location": "src/__tests__/helpers/",
  "fixtures_location": "src/__tests__/fixtures/",
  "patterns": {
    "unit": "direct import, mock adapters at port boundary",
    "integration": "test database, seed before suite, clean after each",
    "e2e": "supertest against running server, test DB"
  },
  "mocking": "vi.mock for module mocking, manual mock adapters for ports",
  "test_database": "separate postgres via docker-compose.test.yml",
  "coverage": "c8, threshold 80%",
  "sample_test_file": "src/domain/__tests__/CreditService.test.ts",
  "key_test_helpers": [
    {"file": "src/__tests__/helpers/createTestUser.ts", "purpose": "factory for test users"},
    {"file": "src/__tests__/helpers/setupTestDb.ts", "purpose": "test DB init and teardown"},
    {"file": "src/__tests__/helpers/mockAdapters.ts", "purpose": "mock implementations of all ports"}
  ]
}
```

---

### 8. CI/CD Analysis

Map build, test, and deploy pipelines.

```bash
# GitHub Actions
find .github/workflows -name "*.yml" -o -name "*.yaml" 2>/dev/null

# Read workflow files
for f in .github/workflows/*.yml; do echo "=== $f ==="; head -30 "$f"; done 2>/dev/null

# Argo CD
find . -path "*/argo/*" -name "*.yml" -o -path "*/argocd/*" -name "*.yaml" 2>/dev/null

# Other CI
find . -name ".gitlab-ci.yml" -o -name "Jenkinsfile" -o -name ".circleci" -o -name "buildkite*" 2>/dev/null

# Deploy scripts
find . -name "deploy*" -type f | head -10

# Environment configs
find . -name "*.env.example" -o -name "*.env.template" | head -5
```

**Output: `ci_cd`**

```json
{
  "ci_system": "github_actions",
  "cd_system": "argo_cd",
  "workflows": [
    {"file": ".github/workflows/ci.yml", "trigger": "PR to main", "steps": ["lint", "type-check", "test", "build"]},
    {"file": ".github/workflows/deploy-staging.yml", "trigger": "merge to main", "steps": ["build", "push image", "argo sync staging"]},
    {"file": ".github/workflows/deploy-prod.yml", "trigger": "manual", "steps": ["build", "push image", "argo sync prod", "smoke test"]}
  ],
  "argo_applications": [
    {"file": "argo/applications/api-server.yml", "target": "api-server", "sync_policy": "auto for staging, manual for prod"}
  ],
  "environments": ["dev (local)", "staging", "production"],
  "secrets_management": "GitHub Secrets + AWS Secrets Manager",
  "docker_registry": "ECR",
  "deployment_strategy": "rolling update (staging), canary via Argo Rollouts (production)",
  "branch_strategy": "trunk-based — feature branches merge to main"
}
```

---

### 9. Observability Analysis

Map monitoring, logging, alerting, and tracing.

```bash
# Metrics / monitoring
grep -rn "prometheus\|datadog\|newrelic\|opentelemetry\|statsd\|metrics" --include="*.ts" --include="*.py" --include="*.yaml" | grep -v node_modules | grep -v test | head -15

# Logging
grep -rn "logger\|pino\|winston\|bunyan\|structlog\|log4j" --include="*.ts" --include="*.py" | grep -v node_modules | grep -v test | head -10

# Alerting
find . -name "*alert*" -o -name "*monitor*" | grep -v node_modules | head -10

# Dashboard configs
find . -name "*dashboard*" -o -name "*grafana*" | head -10

# Health checks
grep -rn "health\|readiness\|liveness" --include="*.ts" --include="*.py" --include="*.yaml" | head -10

# SLO definitions
grep -rn "slo\|SLO\|error_budget\|error.budget" --include="*.ts" --include="*.yaml" --include="*.py" | head -10
```

**Output: `observability`**

```json
{
  "metrics": {
    "system": "opentelemetry → datadog",
    "custom_metrics_location": "src/server/metrics/",
    "pattern": "counter/histogram via OTel SDK"
  },
  "logging": {
    "library": "pino",
    "structured": true,
    "log_level_config": "LOG_LEVEL env var",
    "destination": "stdout → datadog logs"
  },
  "tracing": {
    "system": "opentelemetry",
    "auto_instrumented": ["http", "prisma", "redis"],
    "config": "src/server/tracing.ts"
  },
  "alerting": {
    "system": "datadog monitors",
    "config_location": "infra/monitors/",
    "notification": "PagerDuty for P0/P1, Slack for P2/P3"
  },
  "health_checks": {
    "endpoint": "/health",
    "checks": ["db connectivity", "redis connectivity"]
  },
  "existing_slos": "none defined in code — monitoring is ad hoc",
  "dashboards": "datadog — 3 dashboards found in infra/dashboards/"
}
```

---

### 10. Security Posture Scan

Map auth, secrets, and trust boundaries.

```bash
# Auth middleware and patterns
grep -rn "auth\|authenticate\|authorize\|middleware" --include="*.ts" --include="*.py" | grep -v test | grep -v node_modules | head -15
find . -name "*auth*" -o -name "*guard*" -o -name "*permission*" | grep -v node_modules | grep -v test | head -10

# RBAC / permissions
grep -rn "role\|permission\|rbac\|policy\|can(" --include="*.ts" --include="*.py" | grep -v test | grep -v node_modules | head -10

# Secrets in code (flag for review)
grep -rn "API_KEY\|SECRET\|PASSWORD\|TOKEN\|PRIVATE_KEY" --include="*.ts" --include="*.py" --include="*.env*" | grep -v node_modules | grep -v test | head -10

# Input validation
grep -rn "sanitize\|escape\|validate\|zod\|joi\|yup" --include="*.ts" --include="*.py" | grep -v test | grep -v node_modules | head -10

# CORS config
grep -rn "cors\|CORS\|Access-Control" --include="*.ts" --include="*.py" --include="*.yaml" | grep -v node_modules | head -5

# Rate limiting
grep -rn "rate.limit\|throttle\|rateLimit" --include="*.ts" --include="*.py" | grep -v node_modules | head -5

# Encryption
grep -rn "encrypt\|decrypt\|bcrypt\|argon\|scrypt\|crypto" --include="*.ts" --include="*.py" | grep -v node_modules | grep -v test | head -10
```

**Output: `security`**

```json
{
  "auth": {
    "provider": "clerk",
    "middleware": "src/server/middleware/auth.ts",
    "applied_to": "all /api/ routes",
    "pattern": "JWT verification via Clerk SDK"
  },
  "rbac": {
    "exists": true,
    "location": "src/server/middleware/permissions.ts",
    "roles": ["admin", "member", "viewer"],
    "pattern": "role checked per-route via decorator"
  },
  "input_validation": "zod schemas, validated in route handlers before domain logic",
  "rate_limiting": "express-rate-limit on public endpoints, 100 req/min",
  "cors": "configured in src/server/cors.ts, allow-list based",
  "secrets_management": "env vars in production via AWS Secrets Manager, .env locally",
  "encryption_at_rest": "database-level (RDS encryption)",
  "flagged_concerns": [
    "Found hardcoded API key in src/server/integrations/legacy.ts — may be test key, needs review"
  ]
}
```

---

### 11. Convention Extraction

Synthesize all findings into a conventions guide that coding agents follow.

**Output: `conventions`**

```json
{
  "file_naming": "camelCase for TS files, kebab-case for config, PascalCase for classes",
  "directory_structure": "domain/ for business logic, server/ for infrastructure, __tests__/ co-located",
  "import_style": "relative imports within package, package imports across packages",
  "error_handling": "throw typed DomainError subclasses, catch in route handlers, return structured error response",
  "logging_convention": "logger.info/warn/error with structured context object, never console.log",
  "test_naming": "describe('[ClassName]') → it('should [behavior]')",
  "commit_convention": "conventional commits (feat:, fix:, chore:)",
  "pr_convention": "squash merge, PR title becomes commit message",
  "code_review": "1 approval required, CODEOWNERS for domain/ and auth/",
  "documentation": "JSDoc on public interfaces, README per package"
}
```

---

### 12. Risk Areas

Flag areas of the codebase that are fragile, complex, or high-risk.

```bash
# Files with most changes (hotspots)
git log --format=format: --name-only --since="6 months ago" | sort | uniq -c | sort -rn | head -20

# Large files (complexity risk)
find . -name "*.ts" -o -name "*.py" -o -name "*.scala" | grep -v node_modules | xargs wc -l 2>/dev/null | sort -rn | head -20

# Files with many imports (coupling risk)
for f in $(find . -name "*.ts" -not -path "*/node_modules/*" | head -100); do echo "$(grep -c "import" "$f") $f"; done | sort -rn | head -15

# TODO/FIXME/HACK density
grep -rn "TODO\|FIXME\|HACK\|XXX\|WORKAROUND" --include="*.ts" --include="*.py" | grep -v node_modules | wc -l
grep -rn "TODO\|FIXME\|HACK" --include="*.ts" --include="*.py" | grep -v node_modules | head -10
```

**Output: `risk_areas`**

```json
[
  {
    "file": "src/server/routes/widgetRoutes.ts",
    "reason": "hotspot — 47 changes in 6 months, 380 lines, 12 imports",
    "recommendation": "consider splitting into sub-routers"
  },
  {
    "file": "src/domain/services/CreditService.ts",
    "reason": "280 lines, complex business logic, 8 TODOs",
    "recommendation": "high-risk area for new changes — extra review needed"
  },
  {
    "file": "src/server/integrations/legacy.ts",
    "reason": "hardcoded API key, no tests, 0 changes in 4 months",
    "recommendation": "security review before touching"
  }
]
```

---

### 13. Service Placement Validation

**Goal:** Confirm this is the right service for this feature. Before writing a line of code, verify the feature belongs here and can integrate cleanly.

```bash
# Map service boundaries and ownership
find . -name "Dockerfile*" -o -name "docker-compose*" | head -10
find . -maxdepth 2 -name "package.json" -o -name "go.mod" -o -name "build.sbt" | grep -v node_modules

# Find where related domain concepts live
grep -rn "[PRD_keyword]" --include="*.ts" --include="*.py" --include="*.scala" | grep -v test | grep -v node_modules | head -20

# Check if another service already handles part of this
# (e.g., does a notifications service already exist? A sharing service? An email service?)
find . -path "*/services/*" -type d | head -20
grep -rn "class.*Service\|export.*Service\|trait.*Service" --include="*.ts" --include="*.py" --include="*.scala" | grep -v test | head -20

# Check import graphs — does this service already depend on the right things?
grep -rn "import.*from" --include="*.ts" [affected_paths] | grep -v node_modules | sort | uniq -c | sort -rn | head -20

# Check if the feature would cross service boundaries
# (e.g., does it need data from another service? Does it write to another service's database?)
grep -rn "fetch\|axios\|httpClient\|grpc" --include="*.ts" | grep -v test | grep -v node_modules | head -10
```

**What to determine:**
- Does this service own the domain concept the PRD describes? (e.g., if the PRD is about "sharing deliverables," does this service own "deliverables"?)
- Would this feature be better placed in a different existing service?
- Does this feature require cross-service calls? If so, which services and through what mechanism?
- Does adding this feature violate the service's current responsibility boundary?

**Output: `service_placement`**

```json
{
  "verdict": "correct_service | wrong_service | needs_discussion",
  "reasoning": "string — why this is or isn't the right place",
  "current_service_responsibility": "string — what this service currently does",
  "feature_fit": "string — how the PRD feature aligns (or doesn't) with that responsibility",
  "cross_service_dependencies": [
    {
      "service": "string",
      "why_needed": "string",
      "communication_mechanism": "existing_api | new_api_needed | shared_db | event",
      "location": "string (file path)"
    }
  ],
  "alternative_placement": "string | null — if wrong_service, where it should go"
}
```

---

### 14. Integration Path Analysis

**Goal:** Find every existing library, class, utility, pattern, and loop that this feature can plug into. The default is reuse. New code is the last resort.

```bash
# Find existing classes/modules that handle related concepts
grep -rn "class\|interface\|trait\|export.*function\|export.*const" --include="*.ts" --include="*.py" --include="*.scala" | grep -i "[PRD_concept]" | grep -v test | grep -v node_modules

# Find existing utility libraries the feature should use
find . -path "*/lib/*" -o -path "*/utils/*" -o -path "*/helpers/*" -o -path "*/shared/*" | grep -v node_modules | head -20

# Read the utilities to understand what's available
for f in $(find . -path "*/lib/*" -name "*.ts" -not -path "*/node_modules/*" | head -10); do
  echo "=== $f ==="; head -30 "$f"
done

# Find existing middleware chains the feature should hook into
grep -rn "app.use\|middleware\|preHandler\|plugin" --include="*.ts" | grep -v test | grep -v node_modules | head -15

# Find existing event/hook systems the feature should subscribe to
grep -rn "emit\|on(\|subscribe\|publish\|addEventListener\|hook" --include="*.ts" | grep -v test | grep -v node_modules | head -15

# Find existing base classes, abstract classes, or interfaces to extend
grep -rn "abstract class\|extends\|implements\|trait.*\[" --include="*.ts" --include="*.scala" --include="*.py" | grep -v test | grep -v node_modules | head -20

# Find existing factory/builder patterns
grep -rn "Factory\|Builder\|create.*new\|build(" --include="*.ts" | grep -v test | grep -v node_modules | head -10

# Find existing validation, serialization, and transformation patterns
grep -rn "schema\|validate\|transform\|serialize\|deserialize\|parse" --include="*.ts" | grep -v test | grep -v node_modules | head -15
```

**For each PRD capability, determine:**
1. **Can it extend an existing class?** If there's a `BaseService`, `BaseRepository`, `BaseController` — use it.
2. **Can it hook into an existing loop?** If there's an event system, middleware chain, or plugin architecture — plug into it.
3. **Can it reuse an existing library?** If there's a validation library, HTTP client wrapper, error handler — use it, don't rebuild.
4. **Does it need a new class?** Only if nothing existing covers the concept. And if so, it should follow the same patterns (naming, structure, registration) as existing classes.

**Output: `integration_paths`**

```json
{
  "reuse": [
    {
      "prd_capability": "string — what the PRD needs",
      "existing_component": "string — what already exists",
      "location": "string (file path)",
      "integration_approach": "extend | compose | call | hook_into",
      "what_to_do": "string — specific instruction (e.g., 'extend BaseService, add shareDeliverable method')",
      "confidence": "high | medium | low"
    }
  ],
  "extend": [
    {
      "prd_capability": "string",
      "existing_component": "string — existing class/module to extend",
      "location": "string",
      "what_to_add": "string — specific methods, fields, or hooks",
      "breaking_changes": "none | minor | major"
    }
  ],
  "new_required": [
    {
      "prd_capability": "string",
      "why_new": "string — why nothing existing covers this",
      "follow_pattern_of": "string (file path) — existing class to use as template",
      "proposed_location": "string (file path) — where it should live",
      "proposed_name": "string — following repo naming conventions",
      "must_register_in": "string (file path) — DI container, module, or router where it needs to be wired"
    }
  ],
  "libraries_to_use": [
    {
      "library": "string — existing utility/lib in the repo",
      "location": "string (file path)",
      "use_for": "string — which aspect of the feature"
    }
  ]
}
```

---

### 15. Duplication & Scaffolding Detection

**Goal:** Identify if this feature would duplicate existing patterns, scaffolding, or logic. Duplication is tech debt on arrival. Catch it before it's written.

```bash
# Find existing implementations of similar concepts
grep -rn "share\|invite\|notify\|send.*email\|permission\|access.*control" --include="*.ts" --include="*.py" | grep -v test | grep -v node_modules | head -30

# Find existing permission/access patterns (the PRD likely introduces a new access model)
grep -rn "canAccess\|hasPermission\|isAuthorized\|checkAccess\|grant\|revoke" --include="*.ts" | grep -v test | grep -v node_modules | head -15

# Find existing notification/messaging patterns
grep -rn "notify\|send.*notification\|email\|message\|alert" --include="*.ts" | grep -v test | grep -v node_modules | head -15

# Find existing CRUD scaffolding that might be duplicated
find . -name "*controller*" -o -name "*router*" -o -name "*handler*" | grep -v node_modules | grep -v test | head -15

# Check for existing shared/invite flows
grep -rn "invite\|share\|collaborate\|recipient" --include="*.ts" | grep -v test | grep -v node_modules | head -15
```

**What to flag:**
- **Pattern duplication:** If the repo has a `NotificationService` and the PRD implies building email sending outside of it, flag it. The feature should extend the existing notification pattern, not create a parallel one.
- **Scaffolding duplication:** If the repo has a standard way to create new entities (model + repo + service + router + tests), the feature should follow the same scaffolding. If the agent would generate new scaffolding that diverges from existing patterns, flag it.
- **Logic duplication:** If the repo already has permission checking, access control, or sharing logic (even for a different entity), the feature should reuse that logic, not rewrite it for the new entity.
- **Schema duplication:** If the repo has patterns for tracking "who created what" or "who has access to what," those patterns should be reused, not reinvented.

**Output: `duplication_risks`**

```json
{
  "items": [
    {
      "id": "DUP-001",
      "risk": "string — what would be duplicated",
      "existing_location": "string (file path) — where the existing implementation lives",
      "prd_trigger": "string — which PRD requirement would cause the duplication",
      "recommendation": "reuse_existing | extend_existing | consolidate_first",
      "action": "string — specific instruction to avoid duplication"
    }
  ],
  "scaffolding_convention": {
    "description": "string — how new entities are scaffolded in this repo",
    "example": "string (file paths) — an existing entity that follows the convention",
    "steps": ["string — ordered steps to scaffold a new entity following convention"]
  }
}
```

---

### 16. Scalability & Production Readiness

**Goal:** Assess whether the implementation approach will hold at production scale. Not theoretical — based on current usage patterns, data volumes, and infrastructure found in the repo.

```bash
# Find current scale indicators
grep -rn "limit\|pageSize\|batchSize\|maxResults\|take:" --include="*.ts" | grep -v test | grep -v node_modules | head -15

# Find existing rate limiting, caching, queuing patterns
grep -rn "rateLimit\|cache\|redis\|bull\|queue\|throttle\|debounce" --include="*.ts" | grep -v test | grep -v node_modules | head -15

# Find existing pagination patterns
grep -rn "cursor\|offset\|page\|skip\|take\|limit" --include="*.ts" | grep -v test | grep -v node_modules | head -10

# Find existing batch/async processing
grep -rn "queue\|worker\|job\|async\|background\|cron\|scheduler" --include="*.ts" | grep -v test | grep -v node_modules | head -15

# Check database query patterns (N+1, missing indexes, etc.)
grep -rn "findMany\|findAll\|select\|include:" --include="*.ts" | grep -v test | grep -v node_modules | head -15

# Find connection pool and resource management
grep -rn "pool\|connection\|maxConnections\|timeout" --include="*.ts" --include="*.yaml" --include="*.env*" | grep -v node_modules | head -10
```

**For each PRD capability, assess:**
- **Will the current approach scale?** If the PRD says "searchable dropdown of org users" and the current API returns all users in one call, that won't scale past 1000 users. Flag it.
- **Does it need async processing?** If the PRD involves sending emails to multiple recipients, that should be queued, not synchronous. Check if a queue exists.
- **Does it need caching?** If the feature will be read-heavy (e.g., viewing shared deliverables), check if caching patterns exist.
- **Are there N+1 risks?** If the feature loads entities with relationships (e.g., deliverables with share recipients), check for eager loading patterns.
- **Does the infrastructure support it?** Check if the current DB, cache, and queue can handle the additional load from this feature.

**Output: `scalability`**

```json
{
  "items": [
    {
      "id": "SCALE-001",
      "concern": "string — what won't scale",
      "prd_capability": "string — which feature triggers the concern",
      "current_approach": "string — how it's done now",
      "what_breaks_at_scale": "string — specific failure scenario",
      "recommendation": "string — how to make it scale",
      "existing_pattern_to_follow": "string (file path) | null — if the repo already solves this elsewhere",
      "priority": "must_fix_for_v1 | fix_in_v2 | monitor"
    }
  ],
  "async_processing": {
    "needed_for": ["string — which PRD capabilities need async"],
    "existing_queue": "string (file path) | null",
    "recommendation": "use_existing_queue | add_new_queue | synchronous_ok"
  },
  "caching": {
    "needed_for": ["string — which PRD capabilities benefit from caching"],
    "existing_cache": "string (file path) | null",
    "recommendation": "use_existing_cache | add_cache_layer | not_needed"
  }
}
```

---

### 17. Schema Intelligence

**Goal:** Determine whether the feature needs new schemas, can consolidate with existing schemas, or can extend existing models. New schemas are created only when consolidation is genuinely not possible.

```bash
# Read the full schema
cat prisma/schema.prisma 2>/dev/null || find . -name "schema.prisma" -exec cat {} \; 2>/dev/null

# Find all existing models
grep -n "^model " prisma/schema.prisma 2>/dev/null

# Find relationships and foreign keys
grep -n "relation\|references\|@relation\|@id\|@@index\|@@unique" prisma/schema.prisma 2>/dev/null | head -30

# Find existing patterns for common concerns
# (e.g., how does the repo handle "who created this?", "who has access?", "soft delete?")
grep -n "createdBy\|createdAt\|updatedAt\|deletedAt\|userId\|orgId\|ownerId" prisma/schema.prisma 2>/dev/null

# Find existing enum patterns
grep -n "^enum " prisma/schema.prisma 2>/dev/null

# Find migration history for schema evolution patterns
ls -la prisma/migrations/ 2>/dev/null | tail -15

# Find existing access/permission schemas
grep -n "permission\|access\|role\|share\|invite\|grant" prisma/schema.prisma 2>/dev/null
```

**Decision framework:**

1. **Can the feature reuse an existing model?** If the PRD describes "deliverables" and the schema already has a `Content` or `Output` model, can it be extended with new fields rather than creating a parallel model?

2. **Can the feature extend an existing model?** If a new field or relation is sufficient (e.g., adding `sharedWith` to an existing entity), prefer that over a new table.

3. **Does an existing access/permission pattern cover this?** If the repo already tracks "who has access to what" (e.g., a `Permission` or `Access` table), the share feature should use that pattern, not invent a new one.

4. **If a new model is genuinely needed**, it must:
   - Follow existing naming conventions
   - Use existing patterns for common fields (`createdAt`, `updatedAt`, `orgId`, etc.)
   - Relate to existing models through standard FK patterns
   - Include indexes matching existing query patterns
   - Have a migration that follows existing migration conventions

**Output: `schema_intelligence`**

```json
{
  "existing_models_to_reuse": [
    {
      "model": "string — existing model name",
      "location": "string (schema file + line)",
      "how_to_reuse": "extend_with_fields | add_relation | use_as_is",
      "changes_needed": "string — specific fields or relations to add",
      "migration_complexity": "trivial | moderate | complex"
    }
  ],
  "existing_patterns_to_follow": [
    {
      "pattern": "string (e.g., 'ownership tracking', 'soft delete', 'access control')",
      "example_model": "string — existing model that demonstrates the pattern",
      "apply_to": "string — which new entity should follow this pattern"
    }
  ],
  "new_models_required": [
    {
      "model_name": "string — following repo conventions",
      "why_new": "string — why no existing model covers this",
      "fields": [
        {
          "name": "string",
          "type": "string",
          "rationale": "string — why this field, following which existing pattern"
        }
      ],
      "relations": [
        {
          "to_model": "string",
          "type": "one_to_one | one_to_many | many_to_many",
          "rationale": "string"
        }
      ],
      "indexes": ["string — following existing query patterns"],
      "follows_pattern_of": "string — existing model used as template"
    }
  ],
  "consolidation_opportunities": [
    {
      "description": "string — what could be consolidated",
      "models_involved": ["string"],
      "benefit": "string — why consolidation is better than separate models",
      "risk": "string — what could go wrong with consolidation"
    }
  ]
}
```

---

## Downstream Consumers

| Consumer | What They Use |
|----------|-------------|
| **Build Brief Agent** | `service_placement` + `integration_paths` + `schema_intelligence` — pre-fills the brief with concrete implementation decisions |
| **Eval Council** | `duplication_risks` + `scalability` — validates the brief doesn't introduce duplication or scale problems |
| **Architecture Scaffolding Skill** | `integration_paths` (especially `new_required` and `follow_pattern_of`) + `schema_intelligence` — generates contracts and implementation targets that integrate cleanly |
| **QA Test Data Skill** | `testing`, `data_layer`, `schema_intelligence` — matches test framework and uses correct schema for fixtures |
| **CI/CD Pipeline Skill** | `ci_cd`, `tech_stack` — matches workflow patterns, secrets, deploy strategy |
| **Incident Runbook Skill** | `observability`, `services` — knows monitoring stack, health checks, log locations |
| **Autonomous Coding Agents** | `integration_paths` + `schema_intelligence` + `duplication_risks` — knows what to reuse, extend, or create; never duplicates |
| **Engineer (directly)** | The **Research Deliverable** — service placement verdict, integration paths, duplication warnings, scale concerns, schema recommendations |

---

## MCP Server Contract

### Tool: `analyze_repo`

```json
{
  "name": "analyze_repo",
  "description": "Deep codebase analysis with PRD cross-referencing. Produces repo map, service placement verdict, integration paths, duplication risks, scalability assessment, and schema intelligence.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "repo_path": {
        "type": "string",
        "description": "Path to the repository root"
      },
      "prd_content": {
        "type": "string",
        "description": "Optional PRD markdown. When provided, produces tech debt analysis scoped to PRD requirements and PRD × codebase cross-reference."
      },
      "depth": {
        "type": "string",
        "enum": ["standard", "deep"],
        "default": "deep",
        "description": "standard = structure + patterns. deep = adds tech debt, hotspot analysis, coupling metrics, PRD cross-reference."
      },
      "focus_areas": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Optional — auto-detected from PRD if provided. Manual override for non-PRD analysis."
      }
    },
    "required": ["repo_path"]
  }
}
```

### Tool: `get_repo_section`

```json
{
  "name": "get_repo_section",
  "description": "Retrieve a specific section of a previously generated repo map",
  "inputSchema": {
    "type": "object",
    "properties": {
      "repo_path": {
        "type": "string",
        "description": "Path to the repository (used as cache key)"
      },
      "section": {
        "type": "string",
        "enum": ["meta", "tech_stack", "architecture", "services", "data_layer", "api_surface", "testing", "ci_cd", "observability", "security", "conventions", "risk_areas"],
        "description": "Which section of the repo map to retrieve"
      }
    },
    "required": ["repo_path", "section"]
  }
}
```

### Tool: `diff_repo_changes`

```json
{
  "name": "diff_repo_changes",
  "description": "Compare current repo state against a cached repo map to identify what changed",
  "inputSchema": {
    "type": "object",
    "properties": {
      "repo_path": {
        "type": "string"
      },
      "cached_map_hash": {
        "type": "string",
        "description": "repo_hash from a previous analyze_repo run"
      }
    },
    "required": ["repo_path", "cached_map_hash"]
  }
}
```

---

## CLI Interface

```bash
# Full repo analysis with PRD cross-reference (primary usage)
adlc-repo analyze --repo ./my-repo --prd ./prd.md --output ./research-deliverable.json

# Repo analysis without PRD (standalone)
adlc-repo analyze --repo ./my-repo --depth deep --output ./repo-map.json

# Focus on specific areas (auto-detected from PRD if provided)
adlc-repo analyze --repo ./my-repo --prd ./prd.md --focus email,auth,sharing

# Get specific section
adlc-repo section --repo ./my-repo --section tech_debt

# Get PRD cross-reference only (requires previous analysis)
adlc-repo cross-ref --repo ./my-repo --prd ./prd.md

# Check what changed since last analysis
adlc-repo diff --repo ./my-repo --cached-hash abc123

# Human-readable research deliverable (the starting point for engineers)
adlc-repo deliverable --repo ./my-repo --prd ./prd.md --output ./research-deliverable.md
```

---

## Caching

The repo map is cached by git SHA (or content hash for non-git repos):
- **Cache key:** `{repo_path}:{git_sha}`
- **Cache location:** `.adlc/repo-map.json` in the repo root (gitignored)
- **Invalidation:** Automatically re-runs if git SHA changes
- **Partial refresh:** `diff_repo_changes` identifies only what changed, re-analyzes those sections

---

## Quality Gates

- [ ] All 17 analysis sections produce output (even if "none detected")
- [ ] Architecture pattern detection matches what an engineer would describe
- [ ] File paths in output are valid and exist in the repo
- [ ] Tech stack detection matches package manager manifests
- [ ] Risk areas include at least hotspot analysis
- [ ] Output is valid JSON and parseable by downstream skills
- [ ] Analysis completes in < 90 seconds for repos under 50k files
- [ ] Cached results are returned when repo hasn't changed
- [ ] **Service placement:** Verdict includes reasoning with specific file references
- [ ] **Integration paths:** Every "reuse" item references a real file that exists; every "new_required" item names a pattern to follow with a real reference file
- [ ] **Duplication risks:** Every flagged duplication cites the existing implementation location
- [ ] **Scalability:** Concerns are grounded in actual code (hardcoded limits, missing pagination, synchronous calls) not theoretical
- [ ] **Schema intelligence:** Every proposed model follows conventions found in the existing schema; every consolidation opportunity references specific existing models
- [ ] **When PRD provided:** Every PRD capability maps to exactly one of: reuse, extend, or new_required
- [ ] **Research deliverable is actionable:** An engineer reading it knows what service to build in, what to reuse, what to extend, what to create, and what schema patterns to follow — before opening the Build Brief

## Framework Hardening Addendum

- **Contract versioning:** `analyze_repo` input and output include `contract_version` with semver compatibility rules from `docs/specs/skill-contract-versioning.md`.
- **Schema validation:** Validate emitted repo-map payloads against `docs/schemas/repo-map.schema.json` before caching or returning data.
- **Structured errors:** On validation failure, return structured diagnostics (`field`, `expected_type`, `actual_value`, `version`) instead of partial payloads.
- **Stop reasons:** If analysis cannot continue, emit a terminal reason from `docs/specs/stop-reasons.md` and persist workflow context.
