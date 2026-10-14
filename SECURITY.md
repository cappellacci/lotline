# Security Policy

## Reporting a vulnerability

Please report security issues privately, not in a public issue. Use GitHub's **Private vulnerability reporting**:
the "Report a vulnerability" button under this repository's **Security** tab.

Include enough detail to reproduce the issue. We will acknowledge the report and respond as the challenge timeline
allows.

## Secrets

Secret scanning and push protection are enabled on this repository. API keys live only in a local `.env` (gitignored;
see `.env.example`). If a credential is ever committed, it is rotated immediately; removing it from git history is not
enough once it has been pushed.
