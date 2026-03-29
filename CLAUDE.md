# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Reusable GitHub Actions Workflows and Composite Actions** for the `tonyputi` personal account. Provides centralized CI/CD workflow templates consumed by `tonyputi/*` repositories via `uses: tonyputi/.github/...@main`.

## Repository Structure

```
.github/workflows/                        # Reusable workflow definitions
├── ci.yml                                # CI checks (lint, scan)
├── deploy-laravel-app.yml                # Laravel deploy via SCP + SSH
├── generate-semantic-release.yml         # Semantic versioning via GitHub App
├── lint.yml                              # Lint checks (yaml, shell, dockerfile)
├── release.yml                           # Internal release automation
├── scan-iac.yml                          # IaC security scanning (Checkov)
└── test-php-app.yml                      # PHP test runner

actions/
├── setup/
│   ├── ansible/action.yml                # Ansible + Galaxy collections
│   ├── composer/action.yml               # PHP Composer setup
│   ├── node/action.yml                   # Node.js setup
│   ├── sops/action.yml                   # SOPS installation + age key config
│   └── ssh-key/action.yml                # SSH key + known_hosts setup
└── lint/
    ├── dockerfile/action.yml             # Hadolint
    ├── shell/action.yml                  # ShellCheck
    └── yaml/action.yml                   # yamllint

scripts/
├── create-semantic-release-tags.sh       # Tag creation helper
├── deploy-laravel-app.sh                 # Laravel deployment script
└── generate-env.sh                       # .env file generation

release.config.js                         # Semantic-release configuration
```

## Key Architecture Concepts

### Reusable Workflows
All workflows use `workflow_call` trigger. Consuming repositories reference them at `@main` (or pinned tags after first release):
```yaml
uses: tonyputi/.github/.github/workflows/generate-semantic-release.yml@main
uses: tonyputi/.github/actions/setup/sops@main
```

### GitHub App Authentication
Semantic release uses a GitHub App (not PAT) for token generation:
- Input: `github_app_id` (variable `GH_APP_ID`)
- Secret: `github_app_private_key` (secret `GH_APP_PRIVATE_KEY`)
- Action: `actions/create-github-app-token@v1`

## Common Commands

This repository has no build/test commands. Releases are triggered automatically on push to `main` via `release.yml`.

## Testing Changes

1. Push to a feature branch
2. Test in a consuming repository by temporarily pointing to the branch: `@feature-branch`
3. Once validated, merge to `main` for automatic release

## Conventional Commits

- `feat:` → minor version bump
- `fix:` → patch version bump
- `feat!:` or `BREAKING CHANGE:` → major version bump
- `chore:`, `docs:`, `refactor:` → no release

## Workflow Naming Convention

Workflows follow action-first naming: `<action>-<target>.yml`
- **`deploy-*`**: Deployment workflows
- **`generate-*`**: Generation workflows (releases, etc.)
- **`scan-*`**: Security scan workflows
