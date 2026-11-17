# Reusable GitHub Actions Workflows

Centralized reusable workflows and composite actions for `tonyputi` personal account, shared across `tonyputi/*` repositories.

## Quick Reference

### Workflows

| Workflow                       | Description                                      | Status |
| ------------------------------ | ------------------------------------------------ | ------ |
| [`generate-semantic-release`](#generate-semantic-release) | Automated semantic versioning and releases | Active |
| [`deploy-laravel-app`](#deploy-laravel-app) | Laravel deploy via SCP + SSH            | Active |
| [`test-php-app`](#test-php-app) | PHP test runner                                   | Active |
| [`lint`](#lint)                | Lint checks (yaml, shell, dockerfile)              | Active |
| [`scan-iac`](#scan-iac)        | Security scanning for IaC (Terraform/Ansible/Docker) | Active |
| [`auto-merge`](#dependabot-auto-merge) | Opt Dependabot PRs into native auto-merge | Available |
| [`update-dependabot-branches`](#dependabot-branch-updates) | Update already opted-in Dependabot PR branches | Awaiting pilot |

### Actions

| Action                   | Description                                          |
| ------------------------ | ---------------------------------------------------- |
| [`setup/sops`](#setupsops)         | Install SOPS and configure age key for secrets decryption |
| [`setup/ansible`](#setupansible)   | Install Ansible and Galaxy collections             |
| [`setup/composer`](#setupcomposer) | PHP Composer setup with caching                    |
| [`setup/node`](#setupnode)         | Node.js setup with caching                         |
| [`setup/ssh-key`](#setupssh-key)   | Configure SSH key and known hosts                  |
| [`lint/yaml`](#lintyaml)           | Run yamllint on YAML files                         |
| [`lint/shell`](#lintshell)         | Run ShellCheck on shell scripts                    |
| [`lint/dockerfile`](#lintdockerfile) | Run Hadolint on Dockerfiles                      |

## Usage

Reference workflows and actions at `@main` or at a pinned version tag:

```yaml
# Workflows
uses: tonyputi/.github/.github/workflows/generate-semantic-release.yml@main

# Actions
uses: tonyputi/.github/actions/setup/sops@main
```

---

## Workflow Documentation

### Generate Semantic Release

Automated semantic versioning using semantic-release with GitHub App authentication.

**Features:**
- Automatic version bumping based on conventional commits
- Auto-discovers plugins from `release.config.js` or `release.config.cjs`
- Changelog and GitHub release creation

<details>
<summary>Example usage</summary>

```yaml
jobs:
  release:
    uses: tonyputi/.github/.github/workflows/generate-semantic-release.yml@main
    with:
      github_app_id: ${{ vars.GH_APP_ID }}
    secrets:
      github_app_private_key: ${{ secrets.GH_APP_PRIVATE_KEY }}
```

</details>

**Inputs:**

| Input            | Required | Description          |
| ---------------- | -------- | -------------------- |
| `github_app_id`  | Yes      | GitHub App ID        |

**Secrets:**

| Secret                    | Required | Description               |
| ------------------------- | -------- | ------------------------- |
| `github_app_private_key`  | Yes      | GitHub App private key (PEM) |

**Outputs:**

| Output              | Description                          |
| ------------------- | ------------------------------------ |
| `release_published` | `true` if a new release was created  |
| `release_version`   | The new version number (e.g., `1.2.3`) |

---

### Dependabot Auto-Merge

Opts Dependabot PRs into native squash auto-merge after a successful PR CI run.
GitHub still requires the configured checks and human CODEOWNER approval; if both
are already satisfied, the merge can happen immediately. No approval is submitted.

Before adding the caller, enable repository auto-merge and squash merging, and
require human CODEOWNER approval and reliable checks on the default branch, with
no App bypass. Ensure CODEOWNERS covers the repository. The workflow does not
create or validate these repository settings; Terraform manages them separately.
For this repository, require both `Lint Shell Scripts` and `Lint YAML` as native checks.

Add this caller on the consumer's default branch. Replace `CI` with its actual PR
workflow name and `<reviewed-commit-sha>` with the shared workflow's final reviewed
merge commit SHA:

```yaml
name: Dependabot Auto-Merge

on:
  workflow_run:
    workflows: ['CI']
    types: [completed]

permissions:
  contents: read
  pull-requests: read

jobs:
  auto-merge:
    uses: tonyputi/.github/.github/workflows/auto-merge.yml@<reviewed-commit-sha>
    with:
      github_app_id: ${{ vars.GH_APP_ID }}
    secrets:
      github_app_private_key: ${{ secrets.GH_APP_PRIVATE_KEY }}
```

`github_app_id` (string input) and `github_app_private_key` (secret) are required,
using the same interface as the release workflow. Configure them in the **caller**:
secrets stored in `tonyputi/.github` do not propagate. The App must be installed on
the caller with Contents and Pull requests write permissions; its temporary token
is restricted to that repository and those permissions. Do not give it a ruleset
bypass. An App token, rather than `GITHUB_TOKEN`, lets merges trigger the normal
[push/release workflows](https://docs.github.com/en/actions/concepts/security/github_token).

The `workflow_run` caller allows access to Actions secrets without running PR code.
The reusable reads only PR metadata: it ignores failed/non-PR/fork runs, human PRs,
drafts, closed PRs, other base branches and heads changed since the CI run. It never
checks out code, downloads artifacts, restores caches or executes PR content.
All eligible Dependabot update types are included; titles are not rewritten.
GitHub remains responsible for the current required checks and reviews.

There is no activation flag: adding the caller opts in. To opt out, remove it and
cancel its active runs. Disable auto-merge separately on already queued PRs.

---

### Dependabot Branch Updates

`update-dependabot-branches.yml` complements `auto-merge.yml`. It merges the current
upstream default branch into eligible PR branches using GitHub's non-destructive
update-branch API and an `expected_head_sha` guard. It never opts a PR into auto-merge,
submits approval, merges a PR, force-pushes or changes repository protections.

**Rollout gate:** the shared workflow is not yet adopted here. First review and
merge the implementation, pilot it in `tonyputi/resume` (issue #41 there), and record
a two-PR sequence with fresh CI and enforced human review. Only after that evidence
is recorded, add the caller here under issue #26 and in the separately tracked
consumers. The pilot and this repository's adoption are still pending.

The caller must have repository-owned Dependabot configuration, native auto-merge,
strict required checks, human CODEOWNER approval, stale-approval dismissal and no
App bypass. Keep settings in Terraform. Keep the existing CI-completion auto-merge
caller; this workflow does not replace it. Required check names must remain stable.

The App needs Contents and Pull requests **write**, plus Checks and Commit statuses
**read** to detect failed or pending checks. The token is limited to the caller
repository and these permissions. If the installed App lacks these permissions,
stop and provision them through the separately authorized credential process; do
not silently fall back to a PAT or `GITHUB_TOKEN`. Missing credentials fail the run.

For the pilot, add this small caller on `resume`'s default branch, pinned to the
reviewed shared merge commit. Use the same caller in other consumers only after
the pilot succeeds:

```yaml
name: Update Dependabot Branches

on:
  push:
    branches: ['**']
  schedule:
    - cron: '17 */6 * * *'
  workflow_dispatch:

permissions:
  contents: read

jobs:
  update-branches:
    uses: tonyputi/.github/.github/workflows/update-dependabot-branches.yml@<reviewed-commit-sha>
    with:
      github_app_id: ${{ vars.GH_APP_ID }}
    secrets:
      github_app_private_key: ${{ secrets.GH_APP_PRIVATE_KEY }}
```

The reusable accepts only default-branch pushes (not tags, deletions or PR-head
pushes), scheduled recovery, and manual dispatch. The broad branch trigger follows
default-branch renames without hard-coding `main`; the reusable checks the actual
repository default. Recovery scans run every six hours, subject to GitHub schedule
delays/disablement, and each run is limited to ten minutes with no API retry or
polling. Manual dispatch provides recovery if a push or scheduled event is missed.

Each run fetches current repository/PR metadata and processes PRs serially. A fixed
repository concurrency group prevents overlapping updater runs; active runs are
not cancelled. Pending events can be coalesced because every run scans all open
PRs rather than trusting an event's old head/base SHA. Eligibility requires the
verified Dependabot login and numeric ID, an open non-draft PR, both repositories
matching the caller, the current default base branch, and native auto-merge already
enabled. Forks, human PRs and PRs not opted in are untouched.

Branches already containing the current base need no update. Conflicts fail the
run; failed or pending checks and unknown mergeability are reported without an
update. The workflow checks the current head, base, default branch and eligibility
again before writing. A changed head/base is deferred; a late head race is rejected
by GitHub's expected-head guard. GitHub does not offer an expected-base guard for
this endpoint: a default-branch advance immediately after the final read can still
leave a PR behind. The next push/recovery run handles it; strict native rules block
an outdated merge in the meantime. API errors fail visibly with no immediate retry.

An accepted update uses an App token so `pull_request` synchronization starts fresh
consumer CI. GitHub must enforce checks on the new head; old green checks do not
authorize a merge. Human approvals can be dismissed by the update, and the workflow
never replaces them. Fully unattended merging is not promised: review the new head
and supply a new human approval when required. If fresh CI fails or does not start,
inspect the caller's PR triggers, App permissions and Actions runs; do not bypass
the checks or repeatedly update an already current branch. Resolve conflicts or
failed checks manually, then rerun via dispatch. To opt out, remove the caller and
cancel its runs; disabling existing native auto-merge remains a separate action.

Privileged execution is metadata-only: no checkout, PR code, artifacts or caches.
The workflow downloads `scripts/update-dependabot-branches.js` from an immutable
commit in `tonyputi/.github`, never from the caller or a PR head. Download failures
stop execution before the App token is created. Actions and the script source are
pinned, API metadata is never interpolated into shell source, and errors do not
print API payloads. Live verification must record PR/run URLs for
base advancement, new head/CI, dismissed approval blocking,
repeated events and native auto-merge after valid checks and human review.

---

### Scan IaC

Security scanning for Infrastructure-as-Code using Checkov.

**Features:**
- Supports Terraform, Ansible, Dockerfile, Kubernetes, GitHub Actions
- Configurable skip checks and paths
- Soft fail mode for non-blocking scans

<details>
<summary>Example usage</summary>

```yaml
jobs:
  security:
    uses: tonyputi/.github/.github/workflows/scan-iac.yml@main
    with:
      framework: ansible
      soft_fail: true
      skip_path: 'collections/,.github/'
```

</details>

**Inputs:**

| Input           | Default | Description                                                                 |
| --------------- | ------- | --------------------------------------------------------------------------- |
| `framework`     | `all`   | Framework to scan (`terraform`, `ansible`, `dockerfile`, `kubernetes`, `github_actions`, `all`) |
| `soft_fail`     | `false` | Treat failures as warnings                                                  |
| `skip_checks`   | -       | Comma-separated check IDs to skip                                           |
| `skip_path`     | -       | Comma-separated paths to skip                                               |

---

## Actions Documentation

### setup/sops

Install SOPS and configure age key for secrets decryption.

<details>
<summary>Example usage</summary>

```yaml
- name: Setup SOPS
  uses: tonyputi/.github/actions/setup/sops@main
  with:
    age-key: ${{ secrets.SOPS_AGE_KEY }}
```

</details>

**Inputs:**

| Input     | Required | Default  | Description                    |
| --------- | -------- | -------- | ------------------------------ |
| `version` | No       | `3.8.1`  | SOPS version to install        |
| `age-key` | Yes      | -        | Age private key for decryption |

---

### setup/ansible

Install Ansible and Galaxy collections.

<details>
<summary>Example usage</summary>

```yaml
- name: Setup Ansible
  uses: tonyputi/.github/actions/setup/ansible@main
```

</details>

---

### setup/ssh-key

Configure SSH key and known hosts for remote server access.

<details>
<summary>Example usage</summary>

```yaml
- name: Setup SSH Key
  uses: tonyputi/.github/actions/setup/ssh-key@main
  with:
    ssh_key: ${{ secrets.SERVER_SSH_KEY }}
    hosts: 'example.com'
```

</details>

**Inputs:**

| Input          | Required | Default      | Description                                    |
| -------------- | -------- | ------------ | ---------------------------------------------- |
| `ssh_key`      | Yes      | -            | SSH private key                                |
| `key_name`     | No       | `id_ed25519` | Name for the key file                          |
| `hosts`        | No       | -            | Comma-separated hosts for ssh-keyscan          |
| `known_hosts`  | No       | -            | Known hosts content (alternative to `hosts`)   |

---

### lint/yaml

Run yamllint on YAML files. Auto-detects config files (`.yamllint.yml`, `.yamllint`).

<details>
<summary>Example usage</summary>

```yaml
- name: Lint YAML
  uses: tonyputi/.github/actions/lint/yaml@main
```

</details>

---

### lint/shell

Run ShellCheck on shell scripts.

<details>
<summary>Example usage</summary>

```yaml
- name: Lint shell scripts
  uses: tonyputi/.github/actions/lint/shell@main
  with:
    path: 'scripts'
```

</details>

---

### lint/dockerfile

Run Hadolint on Dockerfiles.

<details>
<summary>Example usage</summary>

```yaml
- name: Lint Dockerfiles
  uses: tonyputi/.github/actions/lint/dockerfile@main
```

</details>

---

## Contributing

1. Place workflows in `.github/workflows/` with action-first naming (`deploy-*`, `scan-*`, `generate-*`)
2. Use `workflow_call` trigger
3. Document all inputs, secrets, and outputs
4. Update this README
5. Use conventional commits:
   - `feat:` → minor version bump
   - `fix:` → patch version bump
   - `feat!:` → major version bump
