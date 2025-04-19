FROM keycloak/keycloak:18.0

COPY keycloak/providers/. /opt/keycloak/providers/
# COPY keycloak/realm-export.json /opt/jboss/keycloak/imports/

RUN ~/./bin/kc.sh build