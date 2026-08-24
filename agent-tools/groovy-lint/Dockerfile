# Groovy linter image — npm-groovy-lint + JRE
#
# GitHub CI (public npm, public apt, no registry secrets):
#   docker build --target public -t groovy-lint agent-tools/groovy-lint
#
# Corp (default stage): public apt for curl/ca-certificates only, then
# corp apt for JRE, then npm from the corp registry.
#   $CONTAINER build $TLS_FLAG \
#     --build-arg PACKAGE_REGISTRY_HOST=<PACKAGE_REGISTRY_HOST> \
#     --build-arg CORP_CA_CERT_URL=<CORP_CA_CERT_URL> \
#     --build-arg DEBIAN_REPO_PATH=<DEBIAN_REPO_PATH> \
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
ARG DEBIAN_REPO_PATH
ARG NPM_VIRTUAL_PATH
ARG DEBIAN_SUITE=bookworm

# Bootstrap: public apt only long enough to fetch the corporate CA.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && curl --insecure -o /usr/local/share/ca-certificates/corp-ca.crt \
       "${CORP_CA_CERT_URL}" \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt

# JRE from the corporate Debian mirror. Credentials live only in this RUN.
# CA is already in the trust store — do not disable TLS verify here.
RUN --mount=type=secret,id=username \
    --mount=type=secret,id=token \
    USERNAME=$(cat /run/secrets/username | cut -d@ -f1) && \
    TOKEN=$(cat /run/secrets/token) && \
    rm -f /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources && \
    echo "# Disabled — using corporate apt mirror" > /etc/apt/sources.list && \
    echo "deb https://${USERNAME}:${TOKEN}@${PACKAGE_REGISTRY_HOST}/${DEBIAN_REPO_PATH} ${DEBIAN_SUITE} main" \
        > /etc/apt/sources.list.d/registry.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends default-jre-headless && \
    rm -rf /var/lib/apt/lists/* && \
    rm -f /etc/apt/sources.list.d/registry.list

RUN --mount=type=secret,id=username \
    --mount=type=secret,id=token \
    USERNAME=$(cat /run/secrets/username | cut -d@ -f1) && \
    TOKEN=$(cat /run/secrets/token) && \
    AUTH_PATH="//${PACKAGE_REGISTRY_HOST}/${NPM_VIRTUAL_PATH}" && \
    printf '%s\n' \
      "registry=https://${PACKAGE_REGISTRY_HOST}/${NPM_VIRTUAL_PATH}" \
      "${AUTH_PATH}:username=${USERNAME}" \
      "${AUTH_PATH}:_password=$(echo -n "${TOKEN}" | base64 | tr -d '\n')" \
      "${AUTH_PATH}:always-auth=true" \
      > /root/.npmrc && \
    npm install -g npm-groovy-lint && \
    rm -f /root/.npmrc && \
    rm -rf /root/.npm

ENTRYPOINT ["npm-groovy-lint"]
