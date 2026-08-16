# Groovy linter image — npm-groovy-lint + JDK
#
# GitHub CI (public npm, no registry secrets):
#   docker build --target public -t groovy-lint agent-tools/groovy-lint
#
# Corp (default stage):
#   $CONTAINER build $TLS_FLAG \
#     --build-arg PACKAGE_REGISTRY_HOST=<PACKAGE_REGISTRY_HOST> \
#     --build-arg CORP_CA_CERT_URL=<CORP_CA_CERT_URL> \
#     --build-arg NPM_VIRTUAL_PATH=<NPM_VIRTUAL_PATH> \
#     --secret id=username,env=REGISTRY_USER \
#     --secret id=token,env=REGISTRY_TOKEN \
#     -t groovy-lint "$AGENT_TOOLS/groovy-lint"

FROM node:lts-slim AS public

RUN apt-get update \
    && apt-get install -y --no-install-recommends default-jre-headless \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g npm-groovy-lint

ENTRYPOINT ["npm-groovy-lint"]

FROM node:lts-slim AS corp

ARG PACKAGE_REGISTRY_HOST
ARG CORP_CA_CERT_URL
ARG NPM_VIRTUAL_PATH

RUN apt-get update \
    && apt-get install -y --no-install-recommends default-jre-headless curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl --insecure -o /usr/local/share/ca-certificates/corp-ca.crt \
    "${CORP_CA_CERT_URL}" \
    && update-ca-certificates

ENV NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt

RUN --mount=type=secret,id=username \
    --mount=type=secret,id=token \
    USERNAME=$(cat /run/secrets/username | cut -d@ -f1) && \
    TOKEN=$(cat /run/secrets/token) && \
    npm install -g npm-groovy-lint \
        --registry "https://${PACKAGE_REGISTRY_HOST}/${NPM_VIRTUAL_PATH}" \
        "--//${PACKAGE_REGISTRY_HOST}/${NPM_VIRTUAL_PATH}:username=${USERNAME}" \
        "--//${PACKAGE_REGISTRY_HOST}/${NPM_VIRTUAL_PATH}:_password=$(echo -n "${TOKEN}" | base64)" \
        "--//${PACKAGE_REGISTRY_HOST}/${NPM_VIRTUAL_PATH}:always-auth=true"

ENTRYPOINT ["npm-groovy-lint"]
