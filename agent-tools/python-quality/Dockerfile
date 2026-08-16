# Python quality audits — invoke lint/format/sec via ruff, mypy, radon, bandit, detect-secrets
#
# GitHub CI (public indexes, no registry secrets):
#   docker build --target public -t python-quality agent-tools/python-quality
#
# Corp (default stage; requires local-agent-tool-base + registry secrets):
#   $CONTAINER build $TLS_FLAG \
#     --build-arg PACKAGE_REGISTRY_HOST=<PACKAGE_REGISTRY_HOST> \
#     --build-arg PIP_INDEX_PATH=<PIP_INDEX_PATH> \
#     --build-arg DEBIAN_REPO_PATH=<DEBIAN_REPO_PATH> \
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

FROM local-agent-tool-base AS corp

ARG PACKAGE_REGISTRY_HOST
ARG PIP_INDEX_PATH
ARG DEBIAN_REPO_PATH

# Python runtime from the corporate apt mirror (base image already has CA certs)
RUN --mount=type=secret,id=username \
    --mount=type=secret,id=token \
    USERNAME=$(cat /run/secrets/username | cut -d@ -f1) && \
    TOKEN=$(cat /run/secrets/token) && \
    echo "deb https://${USERNAME}:${TOKEN}@${PACKAGE_REGISTRY_HOST}/${DEBIAN_REPO_PATH} bookworm main" \
        > /etc/apt/sources.list.d/registry.list && \
    apt-get -o "Acquire::https::Verify-Peer=false" update && \
    apt-get -o "Acquire::https::Verify-Peer=false" install -y --no-install-recommends \
        python3 python3-pip python3-venv python3-dev \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/apt/sources.list.d/registry.list

RUN python3 -m venv /opt/pq-venv
ENV PATH="/opt/pq-venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

RUN --mount=type=secret,id=username \
    --mount=type=secret,id=token \
    REGISTRY_USER=$(cat /run/secrets/username | cut -d@ -f1) && \
    REGISTRY_TOKEN=$(cat /run/secrets/token) && \
    pip install --no-cache-dir \
        --index-url "https://${REGISTRY_USER}:${REGISTRY_TOKEN}@${PACKAGE_REGISTRY_HOST}/${PIP_INDEX_PATH}" \
        --trusted-host "${PACKAGE_REGISTRY_HOST}" \
        invoke ruff mypy radon bandit detect-secrets

COPY tasks /opt/python-quality/tasks
COPY ruff.toml mypy.ini /opt/python-quality/

WORKDIR /workspace
ENTRYPOINT ["invoke", "-r", "/opt/python-quality"]
