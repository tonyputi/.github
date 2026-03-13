# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| v1.x    | :white_check_mark: |
| < v1.0  | :x:                |

## Reporting a Vulnerability

If you discover a security issue, please report it responsibly.

### How to Report

1. **Do NOT** create a public GitHub issue
2. Use [GitHub Security Advisories](https://github.com/tonyputi/.github/security/advisories/new) to report privately
3. Provide as much detail as possible:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### Scope

This policy applies to:
- Reusable GitHub Actions workflows
- Composite actions

### Out of Scope

- Vulnerabilities in third-party actions referenced
- Issues in repositories that consume these workflows

## Security Best Practices

When contributing to this repository:
- Never commit secrets or credentials
- Pin action versions where possible
- Use least-privilege permissions in workflows
- Validate all inputs in scripts
