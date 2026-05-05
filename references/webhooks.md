# Webhooks

> **Phase 2 — not yet built.** This file is a placeholder so an agent loading the SKILL.md reference index doesn't hit a 404.

When this file lands it will cover:

- `webhookCreate` / `webhookUpdate` / `webhookDelete` / `webhookRotateSecret`
- The full event surface: Issue, Comment, Project, Cycle, Reaction, Document, IssueSLA, Attachment, ProjectUpdate, audit log entries
- Secret signing + verification pattern (HMAC-SHA256, `Linear-Signature` header)
- Resource-scoped webhooks (subscribe to one team / project / issue rather than the whole workspace)
- Retry behaviour and the dead-letter queue
- Why this is the **single biggest reason** to use this skill instead of the Linear MCP — the MCP cannot manage webhooks at all

For now: if the agent needs webhook subscription management urgently, run

```bash
uv run python scripts/linear.py introspect WebhookCreateInput
uv run python scripts/linear.py introspect Webhook
```

and compose the mutation directly. The pattern is the same as any other Create — `webhookCreate(input: { url, label, resourceTypes: [...], teamId? })`.

Source: <https://linear.app/developers/webhooks>
