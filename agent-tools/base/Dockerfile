# Corporate base image — certs, apt mirror
# Corp tool images build FROM local-agent-tool-base
#
# MUST pass --build-arg from agents/references/environment.md
# (PACKAGE_REGISTRY_HOST, CORP_CA_CERT_URL, DEBIAN_REPO_PATH).
# No ARG defaults: host and path shapes are vendor-specific.
#
# Build:
#   $CONTAINER build $TLS_FLAG \
#     --build-arg PACKAGE_REGISTRY_HOST=<PACKAGE_REGISTRY_HOST> \
#     --build-arg CORP_CA_CERT_URL=<CORP_CA_CERT_URL> \
#     --build-arg DEBIAN_REPO_PATH=<DEBIAN_REPO_PATH> \
#     --secret id=username,env=REGISTRY_USER \
#     --secret id=token,env=REGISTRY_TOKEN \
#     -t local-agent-tool-base "$AGENT_TOOLS/base"

ARG BASE_IMAGE=debian:bookworm-slim
FROM ${BASE_IMAGE}

ARG PACKAGE_REGISTRY_HOST
ARG CORP_CA_CERT_URL
ARG DEBIAN_REPO_PATH

# Step 1: Fetch corporate CA cert from the package registry
# --insecure required — cert is not yet trusted at this point
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
    && curl --insecure -o /usr/local/share/ca-certificates/corp-ca.crt \
       "${CORP_CA_CERT_URL}" \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Step 2: Replace default Debian apt sources with the corporate apt mirror
RUN rm -f /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources \
    && echo "# Disabled — using corporate apt mirror" > /etc/apt/sources.list

# Step 3: Install base packages from the corporate apt mirror
# Credentials embedded in deb URL — safe because sources.list is created and deleted
# in the same RUN block and never committed to a layer. Token value comes only from
# --mount=type=secret and never appears in image history.
RUN --mount=type=secret,id=username \
    --mount=type=secret,id=token \
    USERNAME=$(cat /run/secrets/username | cut -d@ -f1) && \
    TOKEN=$(cat /run/secrets/token) && \
    echo "deb https://${USERNAME}:${TOKEN}@${PACKAGE_REGISTRY_HOST}/${DEBIAN_REPO_PATH} bookworm main" \
        > /etc/apt/sources.list.d/registry.list && \
    apt-get -o "Acquire::https::Verify-Peer=false" update && \
    apt-get install -y --no-install-recommends \
        gcc g++ make git \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/apt/sources.list.d/registry.list

# Step 4: Set CA bundle env vars for runtime tool use
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
