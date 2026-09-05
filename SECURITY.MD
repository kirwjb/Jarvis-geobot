# Security Policy

## Supported Versions

JARVIS GEO-BOT is currently in active alpha development.

| Version | Supported |
|---------|-----------|
| Latest alpha | ✅ |
| Older releases | ❌ |

## Reporting a Vulnerability

If you discover a security vulnerability in JARVIS GEO-BOT,
please do not report it through a public GitHub Issue.

Please contact the project maintainer privately and provide:

- a description of the vulnerability;
- steps to reproduce it;
- affected component or file;
- potential impact;
- any known mitigation.

Please do not publicly disclose sensitive vulnerability details
before the issue has been investigated and, where possible, fixed.

## Security

JARVIS GEO-BOT uses environment variables for sensitive configuration.

Never commit the following information:

- Telegram bot tokens;
- database credentials;
- Redis credentials;
- API keys;
- private keys;
- production `.env` files.

Use `.env.example` for documenting required environment variables.

## Scope

Security reports may include issues related to:

- Telegram Bot API integration;
- Telegram Mini App;
- authentication and authorization;
- administrator and SUPERADMIN permissions;
- PostgreSQL access;
- Redis sessions and caching;
- API endpoints;
- user data;
- configuration and environment variables.

Thank you for helping keep JARVIS GEO-BOT secure.
