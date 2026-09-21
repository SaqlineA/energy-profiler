# ADR-002: Private Codespaces for browser-based learning

Status: Accepted for private development; not public deployment.
Date: 2026-09-18

## Context

The owner wants to edit code and design from a browser without leaving their
computer running. The Python/SQLite prototype does not have application login.

## Decision

Keep the stack from ADR-001 in a private GitHub repository and Python 3.11 dev
container. Forward port 8000 privately behind GitHub authentication. Permit only
the exact Codespace HTTPS origin derived from GitHub's documented environment
variables; preserve localhost checks. No wildcard hosts or origins. Start the
server explicitly with `python app.py`, so its output and stop control are visible.

## Alternatives and tradeoffs

- Static hosting cannot run Python inference or SQLite.
- Public hosting needs application authentication and an additional security review.
- A tunnel from the original computer still depends on that computer staying on.

## Consequences

This qualifies ADR-001's local-only restriction for an authenticated private
development preview only. GitHub private-port access is the authentication
boundary; hostname checks are not a replacement. Never make the forwarded port
public. Startup accepts only GitHub's `app.github.dev` forwarding domain.
Codespaces stop, incur quota usage, and may expire; they are not permanent hosting.
Recordings/models/secrets remain ignored. Commit and push code; separately export
important generated data. No billing settings are changed by this configuration.

GitHub's live tunnel was observed rewriting both Host and Origin to HTTP
localhost:8000 while retaining X-Forwarded-Proto: https. The entrypoint disables
Uvicorn proxy-header interpretation so same-origin checks compare the internal
scheme consistently. External HTTPS and private-port authentication are unchanged;
no extra origins are trusted to work around this mismatch.
