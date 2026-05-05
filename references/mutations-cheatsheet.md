# Mutations cheatsheet — the gap five

> **Phase 2 — not yet built.** This file is a placeholder so an agent loading the SKILL.md reference index doesn't hit a 404.

When this file lands it will cover the five mutation surfaces that are reachable via the Linear API but **not** via the Linear MCP:

1. **Webhooks CRUD** — see `references/webhooks.md` (also Phase 2).
2. **Cycle and workflow-state mutations**
   - `cycleCreate` / `cycleUpdate` / `cycleArchive`
   - `cycleShiftAll` (move issues from one cycle to another)
   - `cycleStartUpcomingCycleToday`
   - `workflowStateCreate` / `workflowStateUpdate` / `workflowStateArchive`
   - Required for: automated cycle rollover, custom state machines, status-driven flows.
3. **Issue relations, reactions, notification subscriptions**
   - `issueRelationCreate` / `issueRelationUpdate` / `issueRelationDelete` (blocks, duplicates, related)
   - `reactionCreate` / `reactionDelete`
   - `notificationSubscriptionCreate` / `notificationSubscriptionUpdate` / `notificationSubscriptionDelete`
4. **Templates, custom views, favorites**
   - `templateCreate` / `templateUpdate` / `templateDelete`
   - `customViewCreate` / `customViewUpdate` / `customViewDelete`
   - `favoriteCreate` / `favoriteDelete`
5. **Audit log + admin surface**
   - `auditEntries` query
   - `userChangeRole` / `userSuspend` / `userUnsuspend`
   - `organizationInviteCreate` / `organizationInviteUpdate` / `organizationInviteDelete`
   - Integration management mutations (Slack, GitHub, Jira, etc.)

Until this is filled in, introspect the relevant input types and compose the mutations directly:

```bash
uv run python scripts/linear.py introspect CycleCreateInput
uv run python scripts/linear.py introspect WorkflowStateCreateInput
uv run python scripts/linear.py introspect IssueRelationCreateInput
uv run python scripts/linear.py introspect TemplateCreateInput
uv run python scripts/linear.py introspect CustomViewCreateInput
```

The patterns mirror what's in `references/common-queries.md` — call `<entity>Create(input: ...)` and select `success` plus the entity payload.

Sources:
- <https://linear.app/developers/graphql>
- <https://github.com/linear/linear/blob/master/packages/sdk/src/schema.graphql>
