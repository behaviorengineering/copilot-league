# Package Registry Endpoints

Load when generating code that installs packages, pulls images, or authenticates with the corporate package registry (JFrog Artifactory or Sonatype Nexus).

MUST load [environment.md](./environment.md) first. Every hostname, registry path, and credential ID comes from that overlay. `REGISTRY_VENDOR` selects Artifactory vs Nexus path shapes. When generating code, substitute the Value column from `environment.md`. NEVER hardcode `/artifactory/` or `/repository/` except as already present in those Values.

Examples below compose from `environment.md` keys. Substitute the Value column at generation time. NEVER copy hosts or `/artifactory/` vs `/repository/` path shapes from this file.

## Docker Registries

| Purpose | Domain (from `environment.md`) |
|---------|--------|
| Pull (base images, dependencies) | `DOCKER_PULL_DOMAIN` |
| Push (built images) | `DOCKER_PUSH_DOMAIN` |

Pull URL (for `registryUrl` in Jenkins Docker agent): `https://${DOCKER_PULL_DOMAIN}`

Credentials: `DOCKER_CREDS_ID` (Jenkins credential ID)

Nexus Docker uses a connector port or subdomain, not a `/repository/...` path. Put that host:port in `DOCKER_PULL_DOMAIN` / `DOCKER_PUSH_DOMAIN`.

## Python / pip

```
https://${PACKAGE_REGISTRY_HOST}/${PIP_INDEX_PATH}
```

Jenkins `environment` block — bind credentials once at pipeline level using `credentials()`, then interpolate into `PIP_INDEX_URL`:
```groovy
environment {
    REGISTRY      = credentials('<REGISTRY_CREDS_ID>')  // binds REGISTRY_USR + REGISTRY_PSW
    PIP_INDEX_URL = "https://${REGISTRY_USR}:${REGISTRY_PSW}@${PACKAGE_REGISTRY_HOST}/${PIP_INDEX_PATH}"
    PIP_TRUSTED_HOST = "${PACKAGE_REGISTRY_HOST}"
}
```

`PACKAGE_REGISTRY_HOST` and `PIP_INDEX_PATH` are substituted from the Value column before writing the Jenkinsfile (Groovy does not resolve those keys at runtime).

Scripts inherit `PIP_INDEX_URL` and `PIP_TRUSTED_HOST` from the environment — no extra setup needed:
```bash
pip install --index-url "${PIP_INDEX_URL}" --trusted-host "${PIP_TRUSTED_HOST}" -r requirements.txt
```

PROHIBITED — `withCredentials` for pip is unnecessary when credentials are already in `environment {}`:
```groovy
// WRONG — double-binding credentials already set in environment block
withCredentials([usernamePassword(credentialsId: '<REGISTRY_CREDS_ID>', ...)]) { ... }
```

Dockerfile usage (BuildKit secret — never `ARG` or `ENV`). Empty `ARG`s; pass values with `--build-arg` from `environment.md`. Base image: `python:3.12-bookworm`.
```dockerfile
ARG PACKAGE_REGISTRY_HOST
ARG PIP_INDEX_PATH
RUN --mount=type=secret,id=username \
    --mount=type=secret,id=token \
    REGISTRY_USER=$(cat /run/secrets/username | cut -d@ -f1) && \
    REGISTRY_TOKEN=$(cat /run/secrets/token) && \
    pip install \
        --index-url "https://${REGISTRY_USER}:${REGISTRY_TOKEN}@${PACKAGE_REGISTRY_HOST}/${PIP_INDEX_PATH}" \
        --trusted-host ${PACKAGE_REGISTRY_HOST} \
        -r requirements.txt
```

## npm

```
https://${PACKAGE_REGISTRY_HOST}/${NPM_VIRTUAL_PATH}
```

Dockerfile usage (BuildKit secret). Empty `ARG`s; pass values with `--build-arg` from `environment.md`. Base image: `node:lts-slim`.
```dockerfile
ARG PACKAGE_REGISTRY_HOST
ARG NPM_VIRTUAL_PATH
RUN --mount=type=secret,id=username \
    --mount=type=secret,id=token \
    REGISTRY_USER=$(cat /run/secrets/username | cut -d@ -f1) && \
    REGISTRY_TOKEN=$(cat /run/secrets/token) && \
    npm install -g <package-name> \
        --registry "https://${PACKAGE_REGISTRY_HOST}/${NPM_VIRTUAL_PATH}" \
        --//${PACKAGE_REGISTRY_HOST}/${NPM_VIRTUAL_PATH}:username="${REGISTRY_USER}" \
        --//${PACKAGE_REGISTRY_HOST}/${NPM_VIRTUAL_PATH}:_password="$(echo -n "${REGISTRY_TOKEN}" | base64)" \
        --//${PACKAGE_REGISTRY_HOST}/${NPM_VIRTUAL_PATH}:always-auth=true
```

`PACKAGE_REGISTRY_HOST` and `NPM_VIRTUAL_PATH` MUST be Dockerfile `ARG`s with **empty defaults**. Pass `--build-arg` values from `environment.md`.

## Debian apt Mirror

Suite: `bookworm` (Debian 12 — matches `node:lts-slim`, `python:3.12-bookworm` base images)

```
deb https://<REGISTRY_USER>:<REGISTRY_TOKEN>@${PACKAGE_REGISTRY_HOST}/${DEBIAN_REPO_PATH} bookworm main
```

`DEBIAN_REPO_PATH` Value includes the vendor prefix. See `environment.md` § Path Templates.

### Merged apt + CA Cert Layer Pattern (application Dockerfiles)

**CRITICAL — application images:** All apt operations MUST be in ONE merged `RUN` layer. Splitting causes build failure — a separate layer runs `apt-get update` against `deb.debian.org` which is blocked. The corporate apt mirror MUST be configured before any package install.

This merged-layer rule is for **application** Dockerfiles that need apt packages and a CA in one go.

**Tool-image exception:** `python-quality` corp and `groovy-lint` corp bootstrap the CA with `curl --insecure` first (public apt), then use the corp mirror. After `update-ca-certificates`, later apt MUST verify TLS. See those Dockerfiles — do not copy the merged Verify-Peer=false pattern into tool images that already trust the CA.

`Acquire::https::Verify-Peer=false` is required on both `update` and `install` in the application pattern below — the corporate CA cert is not yet trusted when apt runs.

```dockerfile
# One merged layer: disable default repos → corporate apt mirror → install packages → corporate CA cert
# Acquire::https::Verify-Peer=false required: CA cert not trusted yet when apt runs against the registry
ARG PACKAGE_REGISTRY_HOST
ARG DEBIAN_REPO_PATH
ARG CORP_CA_CERT_URL
RUN --mount=type=secret,id=username \
    --mount=type=secret,id=token \
    REGISTRY_USER=$(cat /run/secrets/username | cut -d@ -f1) && \
    REGISTRY_TOKEN=$(cat /run/secrets/token) && \
    rm -f /etc/apt/sources.list.d/*.list && \
    echo "# Disabled - using corporate apt mirror" > /etc/apt/sources.list && \
    echo "deb https://${REGISTRY_USER}:${REGISTRY_TOKEN}@${PACKAGE_REGISTRY_HOST}/${DEBIAN_REPO_PATH} bookworm main" \
        > /etc/apt/sources.list.d/registry.list && \
    apt-get -o "Acquire::https::Verify-Peer=false" update && \
    apt-get -o "Acquire::https::Verify-Peer=false" install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
    && curl --insecure -o /usr/local/share/ca-certificates/corp-ca.crt \
       "${CORP_CA_CERT_URL}" \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/apt/sources.list.d/registry.list

ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt
```

**Rules:**
- Disable default repos FIRST — never run `apt-get update` before the corporate apt mirror is configured
- Remove `registry.list` after install — credentials MUST NOT persist in any layer
- Debian suite MUST match base image (`bookworm` for `node:lts-slim`, `python:3.12-bookworm`)
- All secrets via `--mount=type=secret` — NEVER `ARG` or `ENV`
- CA cert URL MUST be `CORP_CA_CERT_URL` from `environment.md`
- apt `deb` line MUST use `PACKAGE_REGISTRY_HOST` + `DEBIAN_REPO_PATH` from `environment.md` — NEVER hardcode `/artifactory/` or `/repository/`

## Credentials Reference

| Credential ID (Jenkins) | Variables | Used for |
|------------------------|-----------|----------|
| `DOCKER_CREDS_ID` | `REGISTRY_USR`, `REGISTRY_PSW` | Docker login |
| `REGISTRY_CREDS_ID` | `REGISTRY_USR`, `REGISTRY_PSW` | pip, apt, npm |

BuildKit secret IDs (used in Dockerfiles):
- `username` → `REGISTRY_USER` (strip `@...` if the value is an SSO email)
- `token` → `REGISTRY_TOKEN`
