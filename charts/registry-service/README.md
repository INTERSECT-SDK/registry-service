# INTERSECT Registry Service Helm Chart

This chart deploys the INTERSECT registry service and, optionally, the PostgreSQL
database it depends on in the same release.

## Components

- Registry service Deployment and Service
- Optional Ingress
- Optional PostgreSQL StatefulSet and headless Service when `postgresql.enabled=true` (the default)

Two images are used:

| Component | Default image |
| --- | --- |
| Registry service | `ghcr.io/intersect-sdk/registry-service:v0.1.0-rc2` |
| Database | `bitnamilegacy/postgresql:17` |

The database image and its environment variables mirror the `database` service in
the repository's root `docker-compose.yml`.

### Minimum application version

This chart requires an application image in which the Keycloak settings are only
required when `AUTH_IMPLEMENTATION=keycloak`. With `auth.implementation=rudimentary`
the chart renders no `KEYCLOAK_*` variables at all, and an older image rejects that
at startup with `KEYCLOAK_REALM_BASE_URL Field required`. `v0.1.0-rc1` predates the
change; use `v0.1.0-rc2` or newer.

## What this chart does NOT deploy

The **message broker** (RabbitMQ) is not part of this chart. The registry service
connects to an existing broker on startup — it declares the INTERSECT exchange over
AMQP and creates the least-privileged client user through the broker's management
API — so `broker.host` and `broker.managementUri` must point at a reachable RabbitMQ
before the pod will start.

**Keycloak** is likewise not deployed here. The compose file in this repository
includes a Keycloak container for local development only; point
`auth.keycloak.realmBaseUrl` at your institutional auth server instead.

## Install

Minimum viable install against an existing broker, with the database managed by
this release:

```bash
helm upgrade --install registry ./charts/registry-service \
  -n intersect-registry --create-namespace \
  --set app.secretName.hardcoded=<at-least-16-chars> \
  --set app.systemName=<your-system-name> \
  --set auth.implementation=keycloak \
  --set auth.keycloak.realmBaseUrl=https://keycloak.example.com/realms/intersect/protocol/openid-connect \
  --set auth.keycloak.clientId=<oidc-client-id> \
  --set auth.keycloak.clientSecret.hardcoded=<oidc-client-secret> \
  --set auth.session.secret.hardcoded=<random-32-or-64-chars> \
  --set broker.host=<rabbitmq-host> \
  --set broker.managementUri=http://<rabbitmq-host>:15672/ \
  --set broker.root.password.hardcoded=<broker-root-password> \
  --set broker.client.password.hardcoded=<broker-client-password> \
  --set broker.client.apiKey.hardcoded=<broker-client-api-key> \
  --set postgresql.auth.password.hardcoded=<database-password>
```

Or start from an example values file:

```bash
helm upgrade --install registry ./charts/registry-service \
  -n intersect-registry --create-namespace \
  -f ./charts/registry-service/examples/values-no-existing-secret.yaml
```

The chart validates required values at render time, so a missing or malformed
setting fails the install with a specific message instead of producing a pod that
crash-loops on pydantic validation.

## Credential Pattern

Sensitive values use the same structure as the campaign-orchestrator and
broker-http-proxy charts:

```yaml
<field>:
  isSecret: false
  hardcoded: ""
  secretName: ""
  secretKey: ""
```

- `isSecret: false` uses `hardcoded`
- `isSecret: true` reads from `secretName` + `secretKey` via `secretKeyRef`

Credential fields: `app.secretName`, `app.developmentApiKey`,
`auth.keycloak.clientSecret`, `auth.session.secret`, `broker.root.password`,
`broker.client.password`, `broker.client.apiKey`, `postgresql.auth.password`.

For production, prefer `isSecret: true` for all of them:

```bash
helm upgrade --install registry ./charts/registry-service \
  -n intersect-registry --create-namespace \
  -f ./charts/registry-service/examples/values-umbrella-existing-secret.yaml
```

## Authentication

`auth.implementation` selects the auth backend:

- `keycloak` — authenticate against an OIDC provider. Requires
  `auth.keycloak.realmBaseUrl`, `auth.keycloak.clientId`,
  `auth.keycloak.clientSecret` and `auth.session.secret`.
- `rudimentary` — hardcoded in-memory users (`admin`/`admin`,
  `username`/`password`). Local development only.

The `auth.keycloak.*` values are only rendered into the pod when
`auth.implementation=keycloak`, so a `rudimentary` install needs no Keycloak
configuration at all. The chart validates the required Keycloak values at render
time; the application validates the same set at startup and reports every missing
variable at once.

When registering the OIDC client, set its redirect URIs to `${BASE_URL}`,
`${BASE_URL}/login` and `${BASE_URL}/login/callback`.

## Database Options

### Managed by this release (default)

```bash
--set postgresql.enabled=true
```

Creates a single-replica StatefulSet with a headless Service. Persistence is on
by default (`postgresql.persistence.size=8Gi`); set
`postgresql.persistence.storageClass` to match your cluster, or set
`postgresql.persistence.enabled=false` to use an `emptyDir` for throwaway
environments.

Because the application runs Alembic migrations before it binds its port, the
chart adds a `wait-for-database` init container. Disable it with
`postgresql.waitForDatabase=false`.

### External database

```bash
--set postgresql.enabled=false \
--set postgresql.external.host=<db-host> \
--set postgresql.external.port=5432
```

`postgresql.auth.username`, `postgresql.auth.password` and
`postgresql.auth.database` are still used to build the connection.

### Migrations

`app.runMigrations` maps to `ALEMBIC_RUN_MIGRATIONS`. Leave it `true` for normal
use. Set it to `false` only when a DBA applies migrations out of band — the
application then verifies the connection at startup instead of upgrading.

With `replicaCount > 1`, every replica attempts the migrations on startup. Roll
out schema changes with a single replica, or set `app.runMigrations=false` and
apply them separately.

## Service Exposure

Default exposure is an internal `ClusterIP` Service.

NodePort:

```bash
--set service.type=NodePort --set service.nodePort=30050
```

LoadBalancer:

```bash
--set service.type=LoadBalancer
```

Ingress:

```bash
--set ingress.enabled=true \
--set ingress.ingressClassName=nginx \
--set ingress.hostname=registry.example.com \
--set ingress.path=/
```

### Serving under a subpath

If the app is exposed at a subpath, set `app.baseUrl` to that path so generated
links, API documentation and OIDC callback URLs are correct:

```bash
--set ingress.enabled=true \
--set ingress.hostname=example.com \
--set ingress.path=/registry \
--set app.baseUrl=/registry
```

`app.baseUrl` is a path component only — no scheme or host. The proxy must
forward `X-Forwarded-Host` and `X-Forwarded-Proto`; see the repository README for
an nginx example. `app.production` must stay `true` for those headers to be
trusted.

## Health Checks

- Liveness: `GET /api/v1/ping` — returns 204 without touching the database
- Readiness: `GET /api/v1/healthcheck` — verifies the database connection

The application image is distroless, so it has no shell; probes must be HTTP and
`kubectl exec` into the application container is not possible.

## Development Mode

`app.developmentApiKey` maps to `DEVELOPMENT_API_KEY`. Setting it disables broker
ACL creation and API key checks entirely, letting SDK developers skip the UI
workflow. Leave it empty on any deployment reachable outside your control; the
chart prints a warning when it is set.

## Validation

```bash
helm lint ./charts/registry-service -f ./charts/registry-service/examples/values-no-existing-secret.yaml
helm template registry ./charts/registry-service -f ./charts/registry-service/examples/values-no-existing-secret.yaml
```
