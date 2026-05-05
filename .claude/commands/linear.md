---
description: Work assigned Linear issues — fetch, mark in-progress, implement, mark done, comment. Routes through the linear-api skill in this repo.
argument-hint: [optional — issue ID(s), comma-separated, e.g. `AGI-23` or `AGI-23, AGI-26`. Empty = work all assigned in priority order.]
---

# /linear

Work Linear issues end-to-end. All Linear operations go through the **`linear-api` skill** (the sibling `SKILL.md` at the repo root) — never via the deprecated Linear MCP server, which has been removed.

## Identity

The agent operates under whichever auth the loaded skill provides:

- **`linear-api` with OAuth `client_credentials`** (recommended for autonomous use): the OAuth app's bot user — e.g. `ClaudeBot` / `claudebot1`. Comments, issue updates, and audit-log entries attribute to the bot. See `references/auth.md`.
- **`linear-api` with a personal API key**: your user identity. Use for read-only work or `admin`-scope mutations the bot can't perform.

The agent **never** filters with `assignee = "me"` — always resolve to a concrete user or bot ID up-front (the Linear ID-resolution snippets in `references/common-queries.md` cover this).

## Usage

```
/linear                        # Work highest-priority assigned issue → lowest
/linear AGI-23                 # Work the named issue
/linear AGI-23, AGI-26         # Work the listed issues in order
```

## Execution logic

**If `$ARGUMENTS` contains issue IDs:**
1. Parse the comma-separated list.
2. For each ID, fetch the issue (title, description, state, project, labels, parent) via the `linear-api` skill. Work them in the order given.

**If `$ARGUMENTS` is empty:**
1. Resolve the agent's own user ID (run `viewer { id }` once and cache it).
2. List issues where `assignee.id` equals that ID and the state is not `Done` / `Cancelled`.
3. Order by `priority` ascending (1 = Urgent → 4 = Low), then by `updatedAt` descending.
4. Work the highest-priority issue first.

## Standard task workflow (per issue)

1. **Fetch.** Read the issue's full detail via `scripts/linear.py query` using the `Get one issue, with relations` snippet from `references/common-queries.md`.
2. **In Progress.** Move the issue to the team's `In Progress` state via `issueUpdate(id, input: { stateId: ... })`. Resolve the state ID once via the `Get a team's workflow states` query.
3. **Implement.** Do the work. If any code change is involved, branch first per the project's CLAUDE.md trunk-based-dev rule. Apply the project's per-task skill triggers (TDD, intent-audit, requirements-analyst, etc.) as relevant.
4. **Done.** Move the issue to `Done` once the work is complete and tests pass.
5. **Comment.** Post a short summary comment on the issue — what was done, the commit hash(es), the branch, anything the next reader needs to know. The comment is authored by the bot identity loaded above.

## Issue creation conventions

When **creating** Linear issues (whether one-offs or as part of distilling a plan), follow this hierarchy convention. The title prefix gives at-a-glance visibility; the label gives filterability.

### Epics

- **Title prefix**: `Epic - <subject>` (e.g. `Epic - Phase 4 polish`).
- **Label**: apply the **`Epic`** label (orange — `#F2994A`).
- **Parent**: none. Epics are top-level containers.
- **Body**: outline the goal, the stories that hang off it, and the success criteria.

### Stories

- **Title**: no prefix.
- **Label**: apply the **`Story`** label (green — `#27AE60`).
- **Parent**: set `parentId` to the Epic's UUID. Stories are *always* children of an Epic.
- **Body**: user-story-sized scope — small enough to ship in one go.

### Resolving label IDs at use time

Labels are referenced by **UUID** in `IssueCreateInput.labelIds`, but workspace-portability means the agent should resolve them by **name** at use time rather than hardcoding:

```graphql
query LabelIds {
  issueLabels(filter: {
    name: { in: ["Epic", "Story"] }
  }) {
    nodes { id name }
  }
}
```

Cache the result for the session; re-resolve if the cache is stale.

### Setup for a new workspace

If you've cloned this repo into a workspace that doesn't yet have the labels, run this once via the `linear-api` skill:

```graphql
mutation Setup {
  epic: issueLabelCreate(input: {
    name: "Epic", color: "#F2994A",
    description: "Top-level container for a body of work containing 1+ stories. Title prefix 'Epic - '."
  }) { success issueLabel { id name } }
  story: issueLabelCreate(input: {
    name: "Story", color: "#27AE60",
    description: "User-story-sized unit of work; child of an Epic-labelled issue."
  }) { success issueLabel { id name } }
}
```

Workspace-scoped (no `teamId`) so the labels apply across all teams.

## Hard rules

- Never call `mcp__linear-server__*` tools or `mcp__claude_ai_Linear__*` tools. Both are gone — calls will fail.
- Never set `assignee = "me"`. Always resolve to a concrete user or bot ID first.
- Never modify identity fields (`title`, `parent`, `labels`, `project`) the issue body doesn't ask you to change. Identity stays as filed unless the user explicitly authorises a change.
- One workflow state transition per step. Don't jump from `Backlog` to `Done` without `In Progress` in between — the audit trail matters.
- If a workflow needs an operation outside `references/common-queries.md`, run `scripts/linear.py introspect <Type>` to compose the right mutation rather than guessing.
- When creating an Epic, the `Epic` label **and** the `Epic - ` title prefix both apply — neither alone. Same for Stories: the label and the parent link both apply, never one without the other.

## Installation

This command is project-local — it lights up automatically when Claude Code is run from a repo that has this `.claude/commands/linear.md`.

To use it globally across all projects, symlink (or copy) this file:

```bash
ln -s "$(pwd)/.claude/commands/linear.md" ~/.claude/commands/linear.md
```
