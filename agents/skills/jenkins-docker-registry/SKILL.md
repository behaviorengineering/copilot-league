---
name: jenkins-docker-registry
description: 'Corporate Docker registry and Dockerfile constraints (Artifactory or Nexus). Use when writing Docker stages in Jenkinsfiles, Dockerfiles, or build scripts: DOCKER_CONFIG map, pull/push domain separation, dockerArgs (-u root -e HOME=/root), ARG BASE_IMAGE, merged apt+CA cert RUN layer, BuildKit secrets for apt/npm, NO_PROXY for internal hosts, Calculate Image Tags bootstrap agent.'
user-invocable: false
---

# Jenkins Docker Registry

## When to Load

Load when writing Docker stages in Jenkinsfiles, Dockerfiles, or any script that pulls/pushes images or installs packages via the corporate registry (Artifactory or Nexus).

MUST load `.github/agents/references/environment.md` first — every hostname, credential ID, and proxy value comes from that overlay. `REGISTRY_VENDOR` selects Artifactory vs Nexus path shapes. Then load `.github/agents/references/package-registries.md` for apt/npm/pip templates.

Substitute the Value column at generation time. NEVER copy hosts from this file.

## Core Constraints

**CONSTRAINT:** Docker registry MUST be configured as a `DOCKER_CONFIG` map with separate pull and push domains.

Pull and push registries are separate repos — mixing them causes image overwrites or permission failures.

```groovy
def DOCKER_CONFIG = [
    registry: [
        pullDomain: '<DOCKER_PULL_DOMAIN>',
        pullUrl:    'https://<DOCKER_PULL_DOMAIN>',
        pushDomain: '<DOCKER_PUSH_DOMAIN>',
        credentialsId: '<DOCKER_CREDS_ID>'
    ],
    jenkinsAgent: [
        label:      '<JENKINS_AGENT_LABEL>',
        dockerArgs: '-u root -e HOME=/root'
    ],
    images: [
        ciRuntimeImageName: 'my-app-deps',
        appRuntimeImageNamePrefix: 'my-app'
    ]
]
```

Rules:
- `pullDomain`/`pullUrl`: `DOCKER_PULL_DOMAIN` from `environment.md` (read-only, cached base images)
- `pushDomain`: `DOCKER_PUSH_DOMAIN` from `environment.md` (write, built images)
- `dockerArgs: '-u root -e HOME=/root'` MUST be set — NFS workspace requires root; HOME prevents tool path failures
- `credentialsId` MUST be `DOCKER_CREDS_ID` from `environment.md`
- `jenkinsAgent.label` MUST be `JENKINS_AGENT_LABEL` from `environment.md`
- All Docker agent blocks MUST reference `DOCKER_CONFIG.*` fields — NEVER hardcode inline

Docker stage template:
```groovy
agent {
    docker {
        image env.CI_RUNTIME_IMAGE
        args  DOCKER_CONFIG.jenkinsAgent.dockerArgs
        label DOCKER_CONFIG.jenkinsAgent.label
        registryUrl           DOCKER_CONFIG.registry.pullUrl
        registryCredentialsId DOCKER_CONFIG.registry.credentialsId
    }
}
```

**CONSTRAINT:** Dockerfiles MUST pull base images via the corporate pull-through cache using `ARG BASE_IMAGE`.

CORRECT:
```dockerfile
ARG BASE_IMAGE=<DOCKER_PULL_DOMAIN>/python:3.14-bookworm
FROM ${BASE_IMAGE}
```

PROHIBITED:
```dockerfile
FROM python:3.14-bookworm   # Direct Docker Hub — blocked in this environment
```

**CONSTRAINT:** All apt operations MUST be in ONE merged `RUN` layer using BuildKit `--mount=type=secret` — NEVER split into separate layers.

Operations to merge: disable default Debian repos + configure corporate apt mirror + install CA cert + install all packages.

CRITICAL: A separate CA cert layer runs `apt-get update` which hits `deb.debian.org` (blocked). The corporate apt mirror must be configured BEFORE any apt operation.

`Acquire::https::Verify-Peer=false` is required on both `update` and `install` — the CA cert is not trusted yet when apt runs.

For the full merged-layer template, load `.github/agents/references/package-registries.md` § Merged apt + CA Cert Layer Pattern.

Verification:
- All apt + CA cert ops in ONE `RUN` layer: PASS
- CA cert layer separate from apt-mirror setup: FAIL (hits blocked deb.debian.org)
- apt credentials in `ENV` or `ARG`: FAIL (baked into image layer, secrets exposed)
- `registry.list` file removed after apt install: PASS
- `registry.list` file left on filesystem: FAIL (credentials persist in layer)
- Debian suite matches base image (e.g., `bookworm` for `python:3.14-bookworm`): PASS

**CONSTRAINT:** npm packages MUST use the corporate virtual registry from `environment.md` with BuildKit `--mount=type=secret` — NEVER plain `npm install` or hardcoded credentials.

```dockerfile
ARG PACKAGE_REGISTRY_HOST=<PACKAGE_REGISTRY_HOST>
ARG NPM_VIRTUAL_PATH=<NPM_VIRTUAL_PATH>
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

BuildKit secrets injected in the build script:
```bash
DOCKER_BUILDKIT=1 docker build \
    --secret id=username,env=REGISTRY_USER \
    --secret id=token,env=REGISTRY_TOKEN \
    ...
```

**CONSTRAINT:** Proxy MUST exclude internal hosts from routing via `NO_PROXY`.

When `HTTP_PROXY`/`HTTPS_PROXY` is set, all tools (pip, git, curl) route through the proxy — including internal registry calls, which fail with 503.

```groovy
environment {
    HTTP_PROXY  = '<HTTP_PROXY>'
    HTTPS_PROXY = '<HTTP_PROXY>'
    NO_PROXY    = '<NO_PROXY>'
}
```

Symptom without `NO_PROXY`:
```
ProxyError('Cannot connect to proxy.', OSError('Tunnel connection failed: 503 Service Unavailable'))
```

## Verification Checklist

- [ ] `environment.md` loaded; all hosts/IDs match the Value column
- [ ] `DOCKER_CONFIG` map defined at Jenkinsfile top with all required keys
- [ ] All Docker agent blocks reference `DOCKER_CONFIG.*` (no hardcoded registry/label values)
- [ ] `dockerArgs` includes `-u root -e HOME=/root`
- [ ] `REGISTRY_VENDOR` path shapes match `environment.md` (no mixed Artifactory/Nexus URLs)
- [ ] Dockerfile uses `ARG BASE_IMAGE` with `DOCKER_PULL_DOMAIN`, not direct Docker Hub
- [ ] All apt + CA cert ops in one merged `RUN` layer with BuildKit secrets
- [ ] `Acquire::https::Verify-Peer=false` on both `update` and `install`
- [ ] `registry.list` file removed after apt install
- [ ] npm uses corporate virtual registry with BuildKit `--mount=type=secret`
- [ ] `NO_PROXY` set when `HTTP_PROXY`/`HTTPS_PROXY` is set
- [ ] Debian suite in apt mirror matches base image suite
