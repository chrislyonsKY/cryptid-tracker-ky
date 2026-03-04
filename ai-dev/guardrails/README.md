# ai-dev/guardrails/ — Constraint Overview

Guardrails are **hard constraints** that override all other instructions. When a guardrail conflicts with an agent suggestion, the guardrail wins.

## Files

| File | Scope |
|---|---|
| `coding-standards.md` | Language rules, error handling, naming conventions |
| `data-handling.md` | Credentials, Aiven limits, data source attribution, user data |

## Enforcement

Referenced from CLAUDE.md. Every AI session must read these before writing code.
