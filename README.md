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
| [`queue-dependabot`](#queue-dependabot) | Metadata-only native auto-merge opt-in | Dormant; caller opt-in only |

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

### Queue Dependabot

`.github/workflows/queue-dependabot.yml` is a `workflow_call`-only definition. It
never runs itself or activates other repositories. Each consumer keeps a small
`workflow_run` caller and pins this workflow to a **full reviewed commit SHA**.
All repository, owner, default-branch, event and variable context belongs to the
**caller**, not `tonyputi/.github`. Non-`main` default branches are supported.

```yaml
name: Dependabot auto-merge
on:
  workflow_run:
    workflows: [Quality]
    types: [completed]
permissions:
  contents: read
  pull-requests: read
jobs:
  queue:
    if: vars.DEPENDABOT_AUTO_MERGE_ENABLED == 'true'
    uses: tonyputi/.github/.github/workflows/queue-dependabot.yml@<full-reviewed-commit-sha>
    with:
      validation_workflow: .github/workflows/quality.yml
    secrets:
      github_app_private_key: ${{ secrets.DEPENDABOT_QUEUE_APP_PRIVATE_KEY }}
```

**Interface:**

| Name | Source | Required / behavior |
| --- | --- | --- |
| `validation_workflow` | Caller input | Required; expected validation workflow file path |
| `github_app_private_key` | Explicitly mapped caller secret | Optional; absent/empty safely skips queuing |
| `DEPENDABOT_AUTO_MERGE_ENABLED` | Caller Actions variable | Only exact lowercase `true` activates; absent/other values skip |
| `DEPENDABOT_QUEUE_APP_CLIENT_ID` | Caller Actions variable | Absent/empty safely skips queuing |

There are no outputs, repository/branch overrides, or inherited secrets. Set the
variables and secret in the **consumer**, not here. Do not use `secrets: inherit`.
The caller's read-only `GITHUB_TOKEN` verifies metadata; it never performs merges.
The App must be dedicated to the caller repository, installed only there, with
Contents write, Pull requests write and implicit Metadata read, without admin or
bypass rights. No broad multi-repository private key, PAT, or automatic permission
expansion. A pinned action mints a short-lived token scoped to that repository
and those two write permissions, then revokes it after the job. Missing credentials
skip before any metadata API or token creation; invalid configured credentials
fail closed. There is **no `GITHUB_TOKEN` merge fallback**, which could suppress
push-triggered release workflows.

The shared workflow validates the original completed/successful `workflow_run`
from a PR, expected workflow path/ID, caller repository and run head repository,
head SHA and Dependabot branch. It then queries current PR metadata and verifies
Dependabot's bot login, immutable user ID/type, both repositories, default base
branch, tested SHA, open/non-draft state and a unique PR. The merge request uses
`--auto --squash --match-head-commit`; it never approves, bypasses or uses admin.
No checkout, PR code execution, artifact downloads, or caches are permitted in
this privileged workflow. Ordinary PRs remain manual opt-in.

**Protection and rollout are separate requirements:** native auto-merge alone is
not a human gate. Before activation, the caller must have reliable required checks
bound to their source App, a required human CODEOWNER approval, stale approval
dismissal after new commits, and no bypass actors. Bots/AI cannot satisfy that
CODEOWNER gate; an author cannot self-approve.

1. Human-review/merge this shared workflow first. Ensure the consumer pin is the
   final reviewed/merged revision; a squash merge can change the SHA. A feature
   commit pin is only preparation evidence, not proof of the merged revision.
2. Independently verify the consumer latch is disabled before merging its caller
   with green checks. If variables cannot be inspected (the pilot has a 403),
   that confirmation remains a pre-consumer-merge blocker.
3. Separately review/authorize Terraform settings and its normal CI apply; verify
   effective protections. Separately agree/provision the dedicated App credentials,
   then separately authorize setting the latch to exact `true`.
4. Rerun the caller's validation workflow for an existing eligible Dependabot PR;
   record human-gated auto-merge and the post-merge release. Do not claim this from
   offline tests or ordinary PR checks; cross-repository runtime validation may
   remain blocked until the shared revision is merged and its pin confirmed.

The latch is not a live ruleset monitor. Before weakening protections, disable it
**and cancel pending native auto-merge requests**. Disabling the workflow does not
cancel requests already queued. This workflow does not configure repository settings.

Security self-check: `python3 scripts/test-queue-dependabot.py` uses the PyYAML
already installed with the existing yamllint tooling, not a new parsing dependency.
It runs the actual inline Bash/jq with offline API stubs and checks exact activation,
missing credentials, negative event/PR metadata, caller/non-main context, failure
handling, token scope and merge arguments. Existing CI runs it after yamllint.

Pilot references: [shared implementation #17](https://github.com/tonyputi/.github/issues/17),
[Traverse PR #29](https://github.com/tonyputi/traverse/pull/29),
[Traverse rollout #28](https://github.com/tonyputi/traverse/issues/28),
[Terraform PR #111](https://github.com/tonyputi/terraform/pull/111) and
[rollout #110](https://github.com/tonyputi/terraform/issues/110). No fleet rollout,
settings, credentials, merges or applies are authorized by adding this definition.
Broader [#16](https://github.com/tonyputi/.github/issues/16) remains separate.

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
