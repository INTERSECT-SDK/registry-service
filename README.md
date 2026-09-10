# Helm Charts

This GitHub Pages site hosts Helm charts published from the
[registry-service repository](https://github.com/INTERSECT-SDK/registry-service).

## Usage

[Helm](https://helm.sh/) must be installed first.

Add the chart repository:

```bash
helm repo add intersect-registry-service https://intersect-sdk.github.io/registry-service
```

If you already added it before, refresh chart metadata:

```bash
helm repo update
```

List available charts:

```bash
helm search repo intersect-registry-service
```

## Available Charts

- `registry-service`

## Install

The registry service needs an existing message broker and, unless you use the
`rudimentary` auth implementation, an existing OIDC provider. The chart deploys
its own PostgreSQL database by default.

```bash
helm install registry-service intersect-registry-service/registry-service \
  --namespace intersect-registry \
  --create-namespace \
  --set app.secretName.hardcoded=<at-least-16-chars> \
  --set app.systemName=<your-system-name> \
  --set auth.keycloak.realmBaseUrl=<https://keycloak.example.com/realms/intersect/protocol/openid-connect> \
  --set auth.keycloak.clientId=<oidc-client-id> \
  --set auth.keycloak.clientSecret.hardcoded=<oidc-client-secret> \
  --set auth.session.secret.hardcoded=<random-32-or-64-chars> \
  --set broker.host=<rabbitmq-host> \
  --set broker.managementUri=<http://rabbitmq-host:15672/> \
  --set broker.root.password.hardcoded=<broker-root-password> \
  --set broker.client.password.hardcoded=<broker-client-password> \
  --set broker.client.apiKey.hardcoded=<broker-client-api-key> \
  --set postgresql.auth.password.hardcoded=<database-password>
```

For local development you can skip the OIDC provider entirely:

```bash
helm install registry-service intersect-registry-service/registry-service \
  --namespace intersect-registry \
  --create-namespace \
  --set auth.implementation=rudimentary \
  --set app.secretName.hardcoded=<at-least-16-chars> \
  --set auth.session.secret.hardcoded=<random-32-or-64-chars> \
  --set broker.host=<rabbitmq-host> \
  --set broker.managementUri=<http://rabbitmq-host:15672/> \
  --set broker.root.password.hardcoded=<broker-root-password> \
  --set broker.client.password.hardcoded=<broker-client-password> \
  --set broker.client.apiKey.hardcoded=<broker-client-api-key> \
  --set postgresql.auth.password.hardcoded=<database-password>
```

For the full list of values, sourcing credentials from an existing Kubernetes
`Secret`, ingress and subpath setup, see the
[chart README](https://github.com/INTERSECT-SDK/registry-service/blob/main/charts/registry-service/README.md).

## Upgrade

```bash
helm upgrade registry-service intersect-registry-service/registry-service \
  --namespace intersect-registry \
  --reuse-values
```

## Uninstall

```bash
helm uninstall registry-service --namespace intersect-registry
```

Note that uninstalling does not remove the PersistentVolumeClaim created for the
in-release database. Delete it explicitly if you want the data gone.
