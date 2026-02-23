# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it by:

1. **Email**: christophernemala@gmail.com
2. **Subject**: [SECURITY] Job Application Tracker Vulnerability

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

**Do not** create a public GitHub issue for security vulnerabilities.

## Security Best Practices

When deploying this application:

1. **Environment Variables**: Never commit `.env` files or credentials
2. **Database**: Use strong passwords for production databases
3. **HTTPS**: Always deploy with SSL/TLS enabled (Render provides this automatically)
4. **Dependencies**: Keep Python packages updated regularly
5. **Secrets**: Store sensitive data (passwords, API keys) in environment variables

## Automated Security

This repository uses:
- Dependabot for dependency vulnerability alerts
- Secret scanning to prevent credential leaks
- `.gitignore` to exclude sensitive files

## Response Time

We aim to respond to security reports within 48 hours and provide a fix within 7 days for critical vulnerabilities.
