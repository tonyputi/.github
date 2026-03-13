# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Reusable GitHub Actions Workflows and Composite Actions** for the `tonyputi` personal account. Provides centralized CI/CD workflow templates consumed by `tonyputi/*` and `sallemi-iot/*` repositories via `uses: tonyputi/.github/...@main`.

## Repository Structure

```
.github/workflows/           # Reusable workflow definitions
├── generate-semantic-release.yml  # Semantic versioning via GitHub App
├── scan-iac.yml             # IaC security scanning (Checkov)
└── release.yml              # Internal release automation

actions/
├── setup/
│   ├── sops/action.yml      # SOPS installation + age key config
│   ├── ansible/action.yml   # Ansible + Galaxy collections
│   └── ssh-key/action.yml   # SSH key + known_hosts setup
└── lint/
    ├── yaml/action.yml      # yamllint
    ├── shell/action.yml     # ShellCheck
    └── dockerfile/action.yml # Hadolint

release.config.js            # Semantic-release configuration
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
