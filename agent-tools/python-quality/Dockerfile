# Python quality audits — invoke lint/format/sec via ruff, mypy, radon, bandit, detect-secrets
#
# GitHub CI (public indexes, no registry secrets):
#   docker build --target public -t python-quality agent-tools/python-quality
#
# Corp (default stage): CA from CORP_CA_CERT_URL, pip from the corp index.
# Not FROM local-agent-tool-base — interpreter is python:3.12-bookworm.
#   $CONTAINER build $TLS_FLAG \
#     --build-arg PACKAGE_REGISTRY_HOST=<PACKAGE_REGISTRY_HOST> \
#     --build-arg CORP_CA_CERT_URL=<CORP_CA_CERT_URL> \
#     --build-arg PIP_INDEX_PATH=<PIP_INDEX_PATH> \
#     --secret id=username,env=REGISTRY_USER \
#     --secret id=token,env=REGISTRY_TOKEN \
#     -t python-quality "$AGENT_TOOLS/python-quality"
#
# Run (from the task-repo root):
#   $CONTAINER run --rm -v "${PWD}:/workspace" python-quality lint --path /workspace/<file>

FROM python:3.12-bookworm AS public

ENV PYTHONUNBUFFERED=1
RUN pip install --no-cache-dir \
        invoke ruff mypy radon bandit detect-secrets

COPY tasks /opt/python-quality/tasks
COPY ruff.toml mypy.ini /opt/python-quality/

WORKDIR /workspace
ENTRYPOINT ["invoke", "-r", "/opt/python-quality"]

FROM python:3.12-bookworm AS corp

ARG PACKAGE_REGISTRY_HOST
ARG CORP_CA_CERT_URL
ARG PIP_INDEX_PATH

# Bootstrap: public apt only long enough to fetch the corporate CA.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && curl --insecure -o /usr/local/share/ca-certificates/corp-ca.crt \
       "${CORP_CA_CERT_URL}" \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    PYTHONUNBUFFERED=1

RUN --mount=type=secret,id=username \
    --mount=type=secret,id=token \
    REGISTRY_USER=$(cat /run/secrets/username | cut -d@ -f1) && \
    REGISTRY_TOKEN=$(cat /run/secrets/token) && \
    pip install --no-cache-dir \
        --index-url "https://${REGISTRY_USER}:${REGISTRY_TOKEN}@${PACKAGE_REGISTRY_HOST}/${PIP_INDEX_PATH}" \
        invoke ruff mypy radon bandit detect-secrets

COPY tasks /opt/python-quality/tasks
COPY ruff.toml mypy.ini /opt/python-quality/

WORKDIR /workspace
ENTRYPOINT ["invoke", "-r", "/opt/python-quality"]
