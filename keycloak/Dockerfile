FROM quay.io/keycloak/keycloak:26.1.3
ARG KEYCLOAK_REALM_PATH=developer-realm-export.json

WORKDIR /opt/keycloak
USER root

# Replace this with real TLS certificates
#ADD clientkeystore conf/server.keystore
# RUN keytool -genkeypair -storepass password -storetype PKCS12 -keyalg RSA -keysize 2048 -dname "CN=server" -alias server -ext "SAN:c=DNS:localhost,IP:127.0.0.1" -keystore conf/server.keystore
RUN /opt/keycloak/bin/kc.sh build

ADD ${KEYCLOAK_REALM_PATH} /registry_keycloak_realm.json
RUN /opt/keycloak/bin/kc.sh --verbose import --optimized --file /registry_keycloak_realm.json --override true


ENTRYPOINT [ "/opt/keycloak/bin/kc.sh", "start-dev", "--db", "${KC_DB}", "--db-url", "${KC_DB_URL}", "--db-username", "${KC_DB_USERNAME}", "--db-password", "${KC_DB_PASSWORD}" ]
