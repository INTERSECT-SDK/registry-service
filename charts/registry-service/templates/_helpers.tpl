{{- define "registry-service.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "registry-service.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "registry-service.labels" -}}
app.kubernetes.io/name: {{ include "registry-service.name" . }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "registry-service.selectorLabels" -}}
app.kubernetes.io/name: {{ include "registry-service.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "registry-service.fullnameWithSuffix" -}}
{{- $suffix := index . 0 -}}
{{- $context := index . 1 -}}
{{- printf "%s-%s" (include "registry-service.fullname" $context) $suffix | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "registry-service.postgresql.fullname" -}}
{{- include "registry-service.fullnameWithSuffix" (list "postgresql" .) -}}
{{- end -}}

{{- define "registry-service.postgresql.serviceName" -}}
{{- include "registry-service.postgresql.fullname" . -}}
{{- end -}}

{{/*
Host the application uses to reach PostgreSQL: the in-release service when the
database is managed by this chart, otherwise the configured external host.
*/}}
{{- define "registry-service.postgresql.host" -}}
{{- if .Values.postgresql.enabled -}}
{{- include "registry-service.postgresql.serviceName" . -}}
{{- else -}}
{{- .Values.postgresql.external.host -}}
{{- end -}}
{{- end -}}

{{- define "registry-service.postgresql.port" -}}
{{- if .Values.postgresql.enabled -}}
5432
{{- else -}}
{{- .Values.postgresql.external.port -}}
{{- end -}}
{{- end -}}

{{/*
KEYCLOAK_REALM_BASE_URL has no application-side default and must always parse as
a URL, even when Keycloak is not the active auth implementation. Fall back to an
unreachable placeholder so "rudimentary" installs do not need a Keycloak.
*/}}
{{- define "registry-service.keycloak.realmBaseUrl" -}}
{{- $url := trim (default "" .Values.auth.keycloak.realmBaseUrl) -}}
{{- if ne $url "" -}}
{{- $url -}}
{{- else -}}
http://keycloak.invalid/realms/placeholder/protocol/openid-connect
{{- end -}}
{{- end -}}

{{/*
Render one environment variable from a credential block:
  {isSecret, hardcoded, secretName, secretKey}
Usage: include "registry-service.credentialEnv" (list "ENV_NAME" $cred)
*/}}
{{- define "registry-service.credentialEnv" -}}
{{- $name := index . 0 -}}
{{- $cred := index . 1 -}}
- name: {{ $name }}
  {{- if $cred.isSecret }}
  valueFrom:
    secretKeyRef:
      name: {{ $cred.secretName | quote }}
      key: {{ $cred.secretKey | quote }}
  {{- else }}
  value: {{ default "" $cred.hardcoded | quote }}
  {{- end }}
{{- end -}}

{{- define "registry-service.validateCredentialRef" -}}
{{- $path := index . 0 -}}
{{- $cred := index . 1 -}}
{{- if $cred.isSecret -}}
{{- $secretName := trim (default "" $cred.secretName) -}}
{{- $secretKey := trim (default "" $cred.secretKey) -}}
{{- if or (eq $secretName "") (eq $secretKey "") -}}
{{- fail (printf "%s.isSecret=true requires both %s.secretName and %s.secretKey" $path $path $path) -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Fail when a credential is neither sourced from a Secret nor hardcoded.
Usage: include "registry-service.requireCredential" (list "path" $cred)
*/}}
{{- define "registry-service.requireCredential" -}}
{{- $path := index . 0 -}}
{{- $cred := index . 1 -}}
{{- if not $cred.isSecret -}}
{{- if eq (trim (default "" $cred.hardcoded)) "" -}}
{{- fail (printf "%s is required: set %s.hardcoded, or %s.isSecret=true with %s.secretName and %s.secretKey" $path $path $path $path $path) -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "registry-service.validations" -}}
{{- include "registry-service.validateCredentialRef" (list "app.secretName" .Values.app.secretName) -}}
{{- include "registry-service.validateCredentialRef" (list "app.developmentApiKey" .Values.app.developmentApiKey) -}}
{{- include "registry-service.validateCredentialRef" (list "auth.keycloak.clientSecret" .Values.auth.keycloak.clientSecret) -}}
{{- include "registry-service.validateCredentialRef" (list "auth.session.secret" .Values.auth.session.secret) -}}
{{- include "registry-service.validateCredentialRef" (list "broker.root.password" .Values.broker.root.password) -}}
{{- include "registry-service.validateCredentialRef" (list "broker.client.password" .Values.broker.client.password) -}}
{{- include "registry-service.validateCredentialRef" (list "broker.client.apiKey" .Values.broker.client.apiKey) -}}
{{- include "registry-service.validateCredentialRef" (list "postgresql.auth.password" .Values.postgresql.auth.password) -}}

{{- /* SECRET_NAME: required, application enforces a 16 character minimum */ -}}
{{- include "registry-service.requireCredential" (list "app.secretName" .Values.app.secretName) -}}
{{- if not .Values.app.secretName.isSecret -}}
{{- if lt (len (trim .Values.app.secretName.hardcoded)) 16 -}}
{{- fail "app.secretName.hardcoded must be at least 16 characters to satisfy application validation" -}}
{{- end -}}
{{- end -}}

{{- /* SYSTEM_NAME */ -}}
{{- $systemName := trim (default "" .Values.app.systemName) -}}
{{- if not (regexMatch "^[a-z0-9][-a-z0-9]{2,62}$" $systemName) -}}
{{- fail (printf "app.systemName %q must match ^[a-z0-9][-a-z0-9]{2,62}$ to satisfy application validation" $systemName) -}}
{{- end -}}

{{- /* BASE_URL is a path component only */ -}}
{{- $baseUrl := trim (default "" .Values.app.baseUrl) -}}
{{- if and (ne $baseUrl "") (not (hasPrefix "/" $baseUrl)) -}}
{{- fail "app.baseUrl must be a path component beginning with '/' (do not include scheme or host)" -}}
{{- end -}}

{{- /* auth */ -}}
{{- if not (has .Values.auth.implementation (list "keycloak" "rudimentary")) -}}
{{- fail "auth.implementation must be one of: keycloak, rudimentary" -}}
{{- end -}}
{{- if eq .Values.auth.implementation "keycloak" -}}
{{- if eq (trim (default "" .Values.auth.keycloak.realmBaseUrl)) "" -}}
{{- fail "auth.keycloak.realmBaseUrl is required when auth.implementation=keycloak" -}}
{{- end -}}
{{- if eq (trim (default "" .Values.auth.keycloak.clientId)) "" -}}
{{- fail "auth.keycloak.clientId is required when auth.implementation=keycloak" -}}
{{- end -}}
{{- include "registry-service.requireCredential" (list "auth.keycloak.clientSecret" .Values.auth.keycloak.clientSecret) -}}
{{- include "registry-service.requireCredential" (list "auth.session.secret" .Values.auth.session.secret) -}}
{{- end -}}
{{- $realmBaseUrl := trim (default "" .Values.auth.keycloak.realmBaseUrl) -}}
{{- if and (ne $realmBaseUrl "") (not (regexMatch "^https?://" $realmBaseUrl)) -}}
{{- fail "auth.keycloak.realmBaseUrl must be an absolute http(s) URL" -}}
{{- end -}}

{{- /* broker */ -}}
{{- if eq (trim (default "" .Values.broker.host)) "" -}}
{{- fail "broker.host is required" -}}
{{- end -}}
{{- if eq (trim (default "" .Values.broker.managementUri)) "" -}}
{{- fail "broker.managementUri is required" -}}
{{- end -}}
{{- if not (regexMatch "^https?://" (trim .Values.broker.managementUri)) -}}
{{- fail "broker.managementUri must be an absolute http(s) URL" -}}
{{- end -}}
{{- if not (has .Values.broker.protocol (list "amqp0.9.1" "mqtt5.0")) -}}
{{- fail "broker.protocol must be one of: amqp0.9.1, mqtt5.0" -}}
{{- end -}}
{{- if not (has .Values.broker.application (list "rabbitmq")) -}}
{{- fail "broker.application must be one of: rabbitmq" -}}
{{- end -}}
{{- if eq (trim (default "" .Values.broker.root.username)) "" -}}
{{- fail "broker.root.username is required" -}}
{{- end -}}
{{- if eq (trim (default "" .Values.broker.client.username)) "" -}}
{{- fail "broker.client.username is required" -}}
{{- end -}}
{{- include "registry-service.requireCredential" (list "broker.root.password" .Values.broker.root.password) -}}
{{- include "registry-service.requireCredential" (list "broker.client.password" .Values.broker.client.password) -}}
{{- include "registry-service.requireCredential" (list "broker.client.apiKey" .Values.broker.client.apiKey) -}}

{{- /* database */ -}}
{{- include "registry-service.requireCredential" (list "postgresql.auth.password" .Values.postgresql.auth.password) -}}
{{- if eq (trim (default "" .Values.postgresql.auth.username)) "" -}}
{{- fail "postgresql.auth.username is required" -}}
{{- end -}}
{{- if eq (trim (default "" .Values.postgresql.auth.database)) "" -}}
{{- fail "postgresql.auth.database is required" -}}
{{- end -}}
{{- if not .Values.postgresql.enabled -}}
{{- if eq (trim (default "" .Values.postgresql.external.host)) "" -}}
{{- fail "postgresql.external.host is required when postgresql.enabled=false" -}}
{{- end -}}
{{- end -}}

{{- /* ingress */ -}}
{{- if .Values.ingress.enabled -}}
{{- if and (eq (trim (default "" .Values.ingress.hostname)) "") (eq (len .Values.ingress.extraHosts) 0) (eq (len .Values.ingress.extraRules) 0) -}}
{{- fail "ingress.enabled=true requires ingress.hostname, ingress.extraHosts, or ingress.extraRules" -}}
{{- end -}}
{{- end -}}
{{- end -}}
