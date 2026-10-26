---
name: security-threat-model
description: "Threat-model a feature and review code for security. Use when handling user input, auth, money, or personal data."
triggers:
- threat model
- stride
- owasp
- vulnerability
- security review
- auth
---

# Security Threat Model

- Enumerate assets, actors, and trust boundaries; apply STRIDE to each boundary.
- Check the OWASP top risks against the change: injection, broken authz, misconfiguration.
- Secrets never live in code, logs, or the transcript.
- Least privilege for tokens, scopes, and service accounts.
- Record accepted risks explicitly rather than leaving them implicit.
