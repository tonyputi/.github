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

### Deploy Laravel App

Production deployments require a versioned `.env.production` template with no
credentials or personal data. There is no production fallback to `.env.example`.
Other environments can use `.env.<environment>` or fall back to `.env.example`.

Store credentials in the application's GitHub repository secrets, as referenced
by the calling workflow (its reusable-workflow job cannot declare an environment).
Each key in `env_secrets` and `env_overrides` must appear exactly once in the
template. Every
supplied production secret must be non-empty; omit unused optional secrets rather
than passing empty values. Use `toJSON` so quotes, backslashes and newlines remain
valid JSON:

```yaml
jobs:
  deploy:
    uses: tonyputi/.github/.github/workflows/deploy-laravel-app.yml@main
    with:
      environment: production
      github_app_id: ${{ vars.GH_APP_ID }}
    secrets:
      github_app_private_key: ${{ secrets.GH_APP_PRIVATE_KEY }}
      server_ssh_key: ${{ secrets.SERVER_SSH_KEY }}
      env_secrets: |
        {
          "APP_KEY": ${{ toJSON(secrets.APP_KEY) }}
        }
```

The generator uses the application's installed `vlucas/phpdotenv` parser and
checks `APP_ENV=production`, disabled `APP_DEBUG`, and a non-empty `APP_KEY` before
writing `.env` or uploading the release. Secret values must survive parsing
unchanged. Parser error details are suppressed to avoid logging credentials.
Generated `.env` files are owner-readable/writable only during generation and
owner-readable only in the deployed release.

Before enabling a new application, compare its generated environment with its
current production configuration without printing values. Configure all required
GitHub secrets before merging the application's deployment changes. Existing
applications without a production template or with empty declared secrets must
be configured before their next production deployment; their current release is
not changed by a failed generation step.

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
