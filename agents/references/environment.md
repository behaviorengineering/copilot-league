# Corporate Environment Values

Load before generating any Dockerfile, Jenkinsfile, pip/npm/apt/go install, git clone of an internal repo, proxy block, or CA cert fetch. This file is the ONLY source of org-specific hostnames, registry paths, credential IDs, and proxy values.

Shipped values are RFC 2606 placeholders for `REGISTRY_VENDOR=artifactory`. The consuming org MUST set `REGISTRY_VENDOR` to `artifactory` or `nexus`, then replace every Value cell using the matching path template below. Agents MUST read the Value column at generation time and substitute those strings. NEVER invent hosts. NEVER copy hosts from other reference files or prior chats. NEVER emit Artifactory path shapes when `REGISTRY_VENDOR` is `nexus`, or Nexus path shapes when it is `artifactory`.

## Table of Contents
1. [Vendor](#vendor)
2. [Hosts and Paths](#hosts-and-paths)
3. [Path Templates](#path-templates)
4. [Jenkins Identifiers](#jenkins-identifiers)
5. [Auth Rules](#auth-rules)
6. [Git Repositories](#git-repositories)
7. [Substitution Rules](#substitution-rules)

---

## Vendor

| Key | Value | Allowed |
|-----|-------|---------|
| `REGISTRY_VENDOR` | `artifactory` | `artifactory` \| `nexus` |

`artifactory` = JFrog Artifactory. `nexus` = Sonatype Nexus Repository 3. No other vendors.

## Hosts and Paths

Shipped placeholders assume `REGISTRY_VENDOR=artifactory`. A Nexus org MUST replace host **and** every path using the Nexus column in [Path Templates](#path-templates).

| Key | Value | Used for |
|-----|-------|----------|
| `PACKAGE_REGISTRY_HOST` | `artifactory.example.com` | pip, npm, apt, Go proxy, CA cert, `PIP_TRUSTED_HOST` |
| `DOCKER_PULL_DOMAIN` | `docker-snapshot-dependencies.artifactory.example.com` | Base-image pull-through cache |
| `DOCKER_PUSH_DOMAIN` | `docker-snapshot-local.artifactory.example.com` | Image push |
| `PIP_INDEX_PATH` | `artifactory/api/pypi/pypi-virtual/simple` | pip `--index-url` path after host |
| `NPM_VIRTUAL_PATH` | `artifactory/api/npm/npm-virtual/` | npm `--registry` path after host |
| `GOPROXY` | `https://artifactory.example.com/artifactory/api/go/go-dependencies,direct` | `go env -w GOPROXY=...` |
| `DEBIAN_REPO_PATH` | `artifactory/debian-repo` | apt `deb` path after host (includes vendor prefix) |
| `CORP_CA_CERT_URL` | `https://artifactory.example.com/artifactory/generic/security/certificates/corp-ca.pem` | Corporate CA fetch in Dockerfiles |
| `HTTP_PROXY` | `http://proxy.example.com:8080` | `HTTP_PROXY` / `HTTPS_PROXY` |
| `NO_PROXY` | `localhost,127.0.0.1,.internal.example.com,artifactory.example.com` | MUST include `PACKAGE_REGISTRY_HOST` |
| `GIT_SSH_HOST` | `git.example.com` | Internal git clone host when the repo is not `AGENTS_GIT_URL`. Compose `ssh://git@${GIT_SSH_HOST}/...`. NEVER invent a host. |

Derived URLs (do not store separately — compose from the table). Jenkins credential bindings inject `REGISTRY_USR` / `REGISTRY_PSW`. BuildKit and local shells use `REGISTRY_USER` / `REGISTRY_TOKEN` (same login and token; different names). Strip `@...` from `REGISTRY_USER` / `REGISTRY_USR` before Basic auth.

```
DOCKER_PULL_URL     = https://${DOCKER_PULL_DOMAIN}
PIP_INDEX_URL       = https://${REGISTRY_USR}:${REGISTRY_PSW}@${PACKAGE_REGISTRY_HOST}/${PIP_INDEX_PATH}
NPM_REGISTRY        = https://${PACKAGE_REGISTRY_HOST}/${NPM_VIRTUAL_PATH}
APT_MIRROR          = deb https://${REGISTRY_USER}:${REGISTRY_TOKEN}@${PACKAGE_REGISTRY_HOST}/${DEBIAN_REPO_PATH} bookworm main
```

Nexus Docker often uses a connector port (`nexus.example.com:8082`) or a subdomain instead of a path. Put that hostname:port in `DOCKER_PULL_DOMAIN` / `DOCKER_PUSH_DOMAIN`. Do not put `/repository/...` in a Docker registry domain.

## Path Templates

When filling Values, copy the column that matches `REGISTRY_VENDOR`. `<repo>` is the org's repository/group name.

| Key | `artifactory` | `nexus` |
|-----|---------------|---------|
| `PACKAGE_REGISTRY_HOST` | `artifactory.example.com` | `nexus.example.com` |
| `PIP_INDEX_PATH` | `artifactory/api/pypi/<repo>/simple` | `repository/<repo>/simple` |
| `NPM_VIRTUAL_PATH` | `artifactory/api/npm/<repo>/` | `repository/<repo>/` |
| `GOPROXY` | `https://HOST/artifactory/api/go/<repo>,direct` | `https://HOST/repository/<repo>,direct` |
| `DEBIAN_REPO_PATH` | `artifactory/<repo>` | `repository/<repo>` |
| `CORP_CA_CERT_URL` | `https://HOST/artifactory/<raw-repo>/.../corp-ca.pem` | `https://HOST/repository/<raw-repo>/.../corp-ca.pem` |
| `DOCKER_PULL_DOMAIN` | `<repo>.artifactory.example.com` | `nexus.example.com:<port>` or `docker-pull.nexus.example.com` |
| `DOCKER_PUSH_DOMAIN` | `<repo>.artifactory.example.com` | `nexus.example.com:<port>` or `docker-push.nexus.example.com` |

Worked Nexus example (do not use unless `REGISTRY_VENDOR` is `nexus`):

| Key | Example |
|-----|---------|
| `PACKAGE_REGISTRY_HOST` | `nexus.example.com` |
| `PIP_INDEX_PATH` | `repository/pypi-group/simple` |
| `NPM_VIRTUAL_PATH` | `repository/npm-group/` |
| `GOPROXY` | `https://nexus.example.com/repository/go-group,direct` |
| `DEBIAN_REPO_PATH` | `repository/debian-proxy` |
| `CORP_CA_CERT_URL` | `https://nexus.example.com/repository/raw-hosted/security/certificates/corp-ca.pem` |
| `DOCKER_PULL_DOMAIN` | `nexus.example.com:8082` |
| `DOCKER_PUSH_DOMAIN` | `nexus.example.com:8083` |
| `NO_PROXY` | `localhost,127.0.0.1,.internal.example.com,nexus.example.com` |

## Jenkins Identifiers

| Key | Value | Used for |
|-----|-------|----------|
| `DOCKER_CREDS_ID` | `app-docker-creds` | Docker login (`REGISTRY_USR` / `REGISTRY_PSW` from docker creds) |
| `REGISTRY_CREDS_ID` | `app-registry-token` | pip, apt, npm (`REGISTRY_USR` / `REGISTRY_PSW`) |
| `JENKINS_AGENT_LABEL` | `linux-shared` | `DOCKER_CONFIG.jenkinsAgent.label` |

## Auth Rules

| Key | Rule |
|-----|------|
| `REGISTRY_USER` | Login name only. If the shell value is an SSO email, strip the portion from `@` onward: `user@corp.example.com` → `user`. Full email returns HTTP 401. |
| `REGISTRY_TOKEN` | Read from the environment at runtime. NEVER hardcode. NEVER pass as Docker `ARG` or `ENV`. |
| BuildKit secret IDs | `username` → `REGISTRY_USER`, `token` → `REGISTRY_TOKEN`. NEVER `ARG`/`ENV`. Jenkins `credentials()` binds `REGISTRY_USR` / `REGISTRY_PSW` — same values, Jenkins names. |
| `GONOSUMCHECK` | `*` — corporate Go proxies (Artifactory and Nexus) typically do not serve checksum DB entries. MUST be set before every `go install` / `go get`. |

## Git Repositories

| Key | Value | Used for |
|-----|-------|----------|
| `AGENTS_GIT_URL` | `ssh://git@git.example.com/org/copilot-league.git` | Submodule URL for this library at `.github/` |

## Substitution Rules

- MUST load this file before emitting any hostname, registry path, credential ID, proxy value, or internal git URL.
- MUST set `REGISTRY_VENDOR` to `artifactory` or `nexus` and use that vendor's path templates. NEVER mix vendors in one generated file.
- MUST use the Value column as it stands after org customisation. If a Value still contains `example.com`, keep it — do not guess a replacement.
- MUST compose derived URLs from the keys above. NEVER assemble a host from memory. NEVER hardcode `/artifactory/` or `/repository/` except as already present in the Value column.
- MUST keep pull and push Docker domains separate.
- NEVER substitute a public index (Docker Hub, pypi.org, registry.npmjs.org, `proxy.golang.org`, `deb.debian.org`) in generated corporate install/pull paths.
- NEVER leave org-specific names from a previous engagement in generated code.
