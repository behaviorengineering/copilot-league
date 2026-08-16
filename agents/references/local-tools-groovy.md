# Groovy Local Tools — Container Setup

Load when a user asks how to set up local Groovy linting, run npm-groovy-lint, or validate Jenkinsfiles locally.

MUST load [local-tools-container.md](./local-tools-container.md) first. Run **Runtime Detection** and set `$AGENT_TOOLS` from **Path Prefix** before any container command. MUST load [environment.md](./environment.md) and pass its values as `--build-arg` when building the corp stage.

Build and run commands live in [groovy-lint/SKILL.md](../skills/groovy-lint/SKILL.md). This file documents the image layout only. Do not duplicate Jenkins validator Step 4 here.

## Table of Contents
1. [Dockerfile](#dockerfile)
2. [Rules](#rules)

---

## Dockerfile

The live file is `$AGENT_TOOLS/groovy-lint/Dockerfile`. Two stages: `public` (GitHub CI) and `corp` (default, last stage). Do not copy a truncated corp snippet here — open that Dockerfile.

Public build: `docker build --target public -t groovy-lint "$AGENT_TOOLS/groovy-lint"`.

Corp build (default stage) needs `PACKAGE_REGISTRY_HOST`, `CORP_CA_CERT_URL`, `DEBIAN_REPO_PATH`, `NPM_VIRTUAL_PATH`, and BuildKit secrets `username` / `token`. Copy the exact command from the groovy-lint skill.

## Rules

- This image is **not** `FROM local-agent-tool-base`. It starts from `node:lts-slim` so npm is current. Do not rebuild it as a Debian+apt-nodejs image.
- Corp JRE comes from `DEBIAN_REPO_PATH` after the CA is installed. Do not leave `default-jre-headless` on public Debian in the corp stage.
- `default-jre-headless` is required — npm-groovy-lint calls a JVM via CodeNarc. Full JDK is not required.
- NEVER use an Alpine base — the JRE package name and glibc assumptions differ.
- Lint command flags (`--path`, `--files`, `--no-insight`, `--fix`) and Jenkinsfile validation are in the groovy-lint skill, not here.
