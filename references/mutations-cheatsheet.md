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

The three engagement primitives missing from the MCP. None of them are gated behind admin scope — any user-equivalent personal key can write them.

### Issue relations

Mark one issue as related to another. Use cases: "this is a duplicate of AGI-42", "AGI-87 blocks AGI-91", "see also AGI-58".

```graphql
mutation LinkIssues($input: IssueRelationCreateInput!) {
  issueRelationCreate(input: $input) {
    success
    issueRelation { id type issue { identifier } relatedIssue { identifier } }
  }
}
```

```json
{"input": {
  "type": "blocks",
  "issueId": "AGI-87",
  "relatedIssueId": "AGI-91"
}}
```

`type` is the `IssueRelationType` enum:

| Value | Meaning |
|---|---|
| `blocks` | `issueId` blocks `relatedIssueId`. Linear automatically adds the inverse "blocked by" relation. |
| `duplicate` | `issueId` is a duplicate of `relatedIssueId`. |
| `related` | Loose link — informational. |
| `similar` | Surfaced via Linear's similarity detection. |

Both `issueId` and `relatedIssueId` accept a UUID or a human-readable identifier (`AGI-87`). The mutation resolves either form.

`issueRelationUpdate(id, input)` accepts the same fields with everything optional. Note: in the *update* input, `type` is loosely typed as `String` rather than the enum — pass quoted strings (`"blocks"`).

`issueRelationDelete(id)` removes the link. The inverse relation goes with it.

### Reactions

Add an emoji reaction to a comment, issue, project update, or initiative update. The exact same surface emojis use in the Linear UI.

```graphql
mutation React($input: ReactionCreateInput!) {
  reactionCreate(input: $input) {
    success
    reaction { id emoji user { name } }
  }
}
```

`emoji` is required. Then **exactly one** target id — the schema allows several (`commentId`, `issueId`, `projectUpdateId`, `initiativeUpdateId`) but enforces "pick one" server-side. Don't send two; you'll get an error.

```json
{"input": { "emoji": "👍", "commentId": "<comment-uuid>" }}
```

```graphql
mutation Unreact($id: String!) {
  reactionDelete(id: $id) { success }
}
```

`reactionDelete(id)` is hard delete — no trash. To find the reaction id, query the parent's `reactions` field and filter by `user.id` and `emoji`.

### Notification subscriptions

Subscribe an agent (or any user) to events on a specific resource. This is how an agent says "watch this issue / project / cycle for me." It's distinct from webhooks: subscriptions feed Linear's notification system (the bell icon, email digests, push), not a custom HTTP endpoint.

```graphql
mutation Subscribe($input: NotificationSubscriptionCreateInput!) {
  notificationSubscriptionCreate(input: $input) {
    success
    notificationSubscription { id active notificationSubscriptionTypes }
  }
}
```

The input takes **one** of: `customerId`, `customViewId`, `cycleId`, `initiativeId`, `labelId`, `projectId`, `teamId`, `userId`. Pick the resource you want to follow.

```json
{"input": {
  "projectId": "<project-uuid>",
  "notificationSubscriptionTypes": ["issueCreated", "issueStatusChanged", "projectUpdateCreated"],
  "active": true
}}
```

`notificationSubscriptionTypes` is `[String!]` — passing an empty list (or omitting it) subscribes to **all** event types for that resource. Common values: `issueCreated`, `issueStatusChanged`, `issueDueDate`, `projectUpdateCreated`, `commentReaction`. Run `linear.py introspect Mutation` and grep for the related enum if you need the canonical list.

```graphql
mutation UpdateSubscription($id: String!, $input: NotificationSubscriptionUpdateInput!) {
  notificationSubscriptionUpdate(id: $id, input: $input) {
    success
    notificationSubscription { id active notificationSubscriptionTypes }
  }
}
```

`NotificationSubscriptionUpdateInput` only exposes `active` and `notificationSubscriptionTypes`. Pause notifications by setting `active: false` instead of deleting.

**There is no `notificationSubscriptionDelete` mutation.** Linear keeps subscription rows for audit purposes — toggle `active: false` and treat it as deleted. If you need a clean slate, the only way to remove the row entirely is via the UI.

---

## 4. Templates, custom views, favorites

Programmatic provisioning surface. The MCP only reads templates and views (and not always reliably) — the API exposes full CRUD for all three. Useful when an agent stands up a new team's scaffolding rather than just consuming an existing setup.

### Templates

Templates pre-fill an issue, project, or document with a baseline of fields and content. Type is one string of `"issue"`, `"project"`, or `"document"`.

```graphql
mutation CreateTemplate($input: TemplateCreateInput!) {
  templateCreate(input: $input) {
    success
    template { id name type teamId }
  }
}
```

Required: `type`, `name`, `templateData` (JSON object — the baseline payload). `teamId` optional; omit for workspace-level.

```json
{"input": {
  "type": "issue",
  "name": "[Bug] Triage template",
  "description": "Pre-fills the standard bug-report fields.",
  "teamId": "<team-uuid>",
  "templateData": {
    "title": "[Bug] ",
    "description": "## What happened\n\n## Expected\n\n## Repro steps\n",
    "labelIds": ["<bug-label-uuid>"],
    "priority": 3
  }
}}
```

The `templateData` shape mirrors `<Type>CreateInput` for the target entity. For an issue template, it's a partial `IssueCreateInput`-shaped object — same field names, same conventions. Unset fields are blank when the template materialises.

`templateUpdate(id, input)` swaps any of `name`, `description`, `icon`, `color`, `teamId`, `templateData`, `sortOrder`. `templateDelete(id)` is hard delete.

### Custom views

A saved filter + display configuration that shows up in Linear's UI sidebar. The MCP can't create or modify these.

```graphql
mutation CreateView($input: CustomViewCreateInput!) {
  customViewCreate(input: $input) {
    success
    customView { id name shared owner { name } }
  }
}
```

Required: `name`. `filterData` is an `IssueFilter` input — the same filter shape used in `issues(filter: …)` queries (see `references/schema-summary.md`). Pass `shared: true` to make the view visible to everyone in the workspace.

```json
{"input": {
  "name": "P1 bugs across all teams",
  "icon": "AlertCircle",
  "color": "#FF6B6B",
  "filterData": {
    "priority": { "eq": 1 },
    "labels": { "some": { "name": { "eq": "bug" } } }
  },
  "shared": true
}}
```

You can scope a view to one `teamId`, `projectId`, or `initiativeId` instead of leaving it workspace-wide — Linear renders the view inside the relevant area of the UI when scoped. There's also `projectFilterData` (a `ProjectFilter`) for project-style views and `feedItemFilterData` for activity-feed views.

`customViewUpdate(id, input)` accepts the same fields with everything optional. `customViewDelete(id)` is hard delete; users who had it favorited lose the link.

### Favorites

Favorites are the items in a user's sidebar pin list. Each favorite points at **one** target entity. The schema lists many possible target ids (`issueId`, `projectId`, `cycleId`, `customViewId`, `documentId`, `labelId`, `userId`, `customerId`, `releaseId`, `dashboardId`, etc.) — supply exactly one. Server-side enforces it.

```graphql
mutation Pin($input: FavoriteCreateInput!) {
  favoriteCreate(input: $input) {
    success
    favorite { id sortOrder folderName }
  }
}
```

```json
{"input": {
  "issueId": "AGI-87",
  "folderName": "Right now"
}}
```

`folderName` groups the favorite into a named folder; pass a `parentId` to nest under an existing folder. Folders themselves are favorites with a `folderName` and no target id.

```graphql
mutation MovePin($id: String!, $input: FavoriteUpdateInput!) {
  favoriteUpdate(id: $id, input: $input) {
    success
    favorite { id sortOrder folderName parent { id } }
  }
}

mutation Unpin($id: String!) { favoriteDelete(id: $id) { success } }
```

`favoriteUpdate` only changes `sortOrder`, `parentId`, or `folderName` — you can't switch a favorite from one target to another. To change targets, delete and recreate.

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
