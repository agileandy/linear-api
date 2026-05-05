# Mutations cheatsheet — the gap five

> **Index** — [1. Webhooks](#1-webhooks-crud) · [2. Cycles & workflow states](#2-cycles--workflow-states) · [3. Relations, reactions, subscriptions](#3-relations-reactions-subscriptions) · [4. Templates, custom views, favorites](#4-templates-custom-views-favorites) · [5. Audit log & admin](#5-audit-log--admin)

This file covers the five mutation surfaces reachable via the Linear API but **not** via the Linear MCP. These are the operations that justify writing a skill at all — for everything else, the MCP is fine.

For the read paths, MCP-parity write paths, and entity model, see `references/common-queries.md` and `references/schema-summary.md`.

---

## 1. Webhooks CRUD

Lives in its own file: see **`references/webhooks.md`** for the full reference (resource types, signing, delivery semantics, common pitfalls). It's broken out because webhooks are the single biggest reason to use this skill instead of the MCP, and the receiver-side concerns (signature verification, idempotency) deserve their own page.

---

## 2. Cycles & workflow states

The MCP is read-only on both. The API exposes full CRUD plus two cycle-flow conveniences (`shiftAll`, `startUpcomingCycleToday`). Required for: automated cycle rollover, slip-the-sprint workflows, custom state-machine provisioning, status-driven automation.

### Create a cycle

Required: `teamId`, `startsAt`, `endsAt`. `name` is optional — Linear auto-numbers cycles per team if you omit it.

```graphql
mutation CreateCycle($input: CycleCreateInput!) {
  cycleCreate(input: $input) {
    success
    cycle { id number name startsAt endsAt }
  }
}
```

```json
{"input": {
  "teamId": "<team-uuid>",
  "name": "Sprint 12 — auth refactor",
  "description": "Wrap up the OAuth migration; ship the new token store.",
  "startsAt": "2026-05-12T00:00:00.000Z",
  "endsAt": "2026-05-26T00:00:00.000Z"
}}
```

### Update a cycle

Pass `id` as a top-level arg, plus a partial `CycleUpdateInput`. **`teamId` is not in the update input** — cycles can't be moved between teams.

```graphql
mutation UpdateCycle($id: String!, $input: CycleUpdateInput!) {
  cycleUpdate(id: $id, input: $input) {
    success
    cycle { id name startsAt endsAt completedAt }
  }
}
```

```json
{"id": "<cycle-uuid>", "input": { "endsAt": "2026-05-30T00:00:00.000Z" }}
```

### Archive a cycle

```graphql
mutation ArchiveCycle($id: String!) {
  cycleArchive(id: $id) { success }
}
```

Archiving hides the cycle from default UI and most queries. To list archived cycles, pass `includeArchived: true` to the connection.

### Shift all cycles by N days

The slip-the-sprint move. From a starting cycle, all subsequent cycles shift forward by `daysToShift` days. Useful when a team commits and reality slips by a sprint.

```graphql
mutation ShiftCycles($input: CycleShiftAllInput!) {
  cycleShiftAll(input: $input) {
    success
  }
}
```

```json
{"input": { "id": "<starting-cycle-uuid>", "daysToShift": 7 }}
```

`daysToShift` is a `Float`. Negative values pull cycles earlier — confirm with the user before running this; it's destructive in the sense that scheduled work shifts under everyone's feet.

### Start the upcoming cycle today

For when a cycle is scheduled to begin tomorrow but the team is ready now:

```graphql
mutation StartNow($id: String!) {
  cycleStartUpcomingCycleToday(id: $id) { success }
}
```

The `id` is the upcoming cycle's id (not the active one). Linear adjusts `startsAt` to today and shifts the active cycle's `endsAt` to match.

### Workflow states — create

Required: `teamId`, `type` (string — see enum below), `name`, `color`. `type` is `String!` not an enum input — pass quoted strings.

```graphql
mutation CreateState($input: WorkflowStateCreateInput!) {
  workflowStateCreate(input: $input) {
    success
    workflowState { id name type color position }
  }
}
```

```json
{"input": {
  "teamId": "<team-uuid>",
  "type": "started",
  "name": "In Review",
  "color": "#5E6AD2",
  "description": "PR open, awaiting code review.",
  "position": 2.5
}}
```

`type` enum values:

| Value | Meaning |
|---|---|
| `triage` | Inbox, not yet refined |
| `backlog` | Refined but not committed |
| `unstarted` | Committed, not started |
| `started` | Work in progress |
| `completed` | Done |
| `canceled` | Won't do |

Each team needs at least one state of each functional type (Linear enforces this). `position` is a float for ordering — pick a value between two existing states, like `2.5` to slot between positions 2 and 3.

### Workflow states — update

Note: **`type` is not in the update input**. To change a state's type, archive the old one and create a new one with the right type.

```graphql
mutation UpdateState($id: String!, $input: WorkflowStateUpdateInput!) {
  workflowStateUpdate(id: $id, input: $input) {
    success
    workflowState { id name color position }
  }
}
```

### Workflow states — archive

```graphql
mutation ArchiveState($id: String!) {
  workflowStateArchive(id: $id) { success }
}
```

Linear refuses to archive a state that issues are currently in. Move issues out (`issueUpdate(id, input: { stateId: ... })`) first.

---

## 3. Relations, reactions, subscriptions

> **Phase 2 — section in progress.** Until this fills in, introspect:
>
> ```bash
> uv run python scripts/linear.py introspect IssueRelationCreateInput
> uv run python scripts/linear.py introspect ReactionCreateInput
> uv run python scripts/linear.py introspect NotificationSubscriptionCreateInput
> ```
>
> The mutations are: `issueRelationCreate / Update / Delete`, `reactionCreate / Delete`, `notificationSubscriptionCreate / Update / Delete`. They follow the same pattern as everything else — `input: <Op>Input` on create, `id` + partial `input` on update, `id` only on delete.

---

## 4. Templates, custom views, favorites

> **Phase 2 — section in progress.** Until this fills in, introspect:
>
> ```bash
> uv run python scripts/linear.py introspect TemplateCreateInput
> uv run python scripts/linear.py introspect CustomViewCreateInput
> uv run python scripts/linear.py introspect FavoriteCreateInput
> ```
>
> Mutations: `templateCreate / Update / Delete`, `customViewCreate / Update / Delete`, `favoriteCreate / Delete` (no update — favorites are a leaf).

---

## 5. Audit log & admin

> **Phase 2 — section in progress.** Until this fills in, introspect:
>
> ```bash
> uv run python scripts/linear.py introspect AuditEntryFilter
> uv run python scripts/linear.py introspect Mutation   # grep for organizationInvite, userChangeRole, integration*
> ```
>
> Read path: `auditEntries(filter:)` returns workspace audit-log rows. Mutations: `userChangeRole`, `userSuspend`, `userUnsuspend`, `organizationInviteCreate / Update / Delete`, plus the integration-management mutations (`integrationSlack*`, `integrationGithub*`, etc — names track the integration).
>
> The `admin` OAuth scope is required for most of these. Personal API keys also work if the owning user is a workspace admin.

---

Sources:
- <https://linear.app/developers/graphql>
- <https://github.com/linear/linear/blob/master/packages/sdk/src/schema.graphql>
