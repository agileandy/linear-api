# Linear API as an Integration Layer — Plan

**Author:** Andy
**Date:** 2026-05-05
**Status:** Draft for review

## The case

MCP loads every tool definition into the agent's context on every turn. With Linear's MCP that's ~40 tool schemas burning tokens whether the agent touches Linear or not. A skill loads on demand, then does progressive discovery — read a SKILL.md, pick the right GraphQL operation, run it. Less context, more focus, and the agent only learns the bits of Linear it actually needs.

The catch: the API is GraphQL, so the skill has to teach the agent how to compose queries instead of handing it pre-baked tools. That's a one-time cost. After that, the API beats MCP on three fronts — coverage, token cost, and control over what gets fetched (GraphQL only returns the fields you ask for).

## What MCP covers today

| Domain | MCP support |
|---|---|
| Issues | get / list / save (no delete) |
| Comments | list / save / delete |
| Projects | get / list / save + project_labels list |
| Initiatives | get / list / save |
| Milestones | get / list / save |
| Cycles | **list only** |
| Teams | get / list (read-only) |
| Users | get / list (read-only) |
| Workflow states | get / list (read-only) |
| Issue labels | list / **create only** |
| Documents | get / list / save |
| Attachments | get / create / delete / extract_images |
| Customers | list / save / delete |
| Customer needs | save / delete |
| Status updates | get / save / delete |
| Documentation | search |

Roughly 40 tools. Solid for read paths and basic writes. Read-heavy or low-touch workflows will work fine on MCP forever.

## Where the API pulls ahead — top 5 gaps

Ordered by impact for an agent integration:

1. **Webhooks (full CRUD).** API has `webhookCreate/Update/Delete/RotateSecret` across Issue, Comment, Project, Cycle, Reaction, Document, IssueSLA, audit log, and more. MCP has zero. Without webhooks, every agent reduces to polling — wasteful and laggy.
2. **Cycle and workflow-state mutations.** `cycleCreate/Update/Archive/ShiftAll/StartUpcomingCycleToday` and `workflowStateCreate/Update/Archive`. MCP is read-only on both. Blocks anything sprint-shaped — automated cycle rollover, custom state machines, status-driven flows.
3. **Issue relations, reactions, notification subscriptions.** Three engagement primitives missing from MCP. Need to mark a duplicate, react to a comment, or subscribe an agent to "watch this issue"? Only the API does it.
4. **Templates, custom views, favorites.** Programmatic provisioning. An agent can stand up a new team's view and template scaffolding instead of just reading existing ones.
5. **Audit log + admin surface.** `auditEntries` query, `userChangeRole`, `userSuspend`, `organizationInvite*`, plus the integrations management API (Slack/GitHub/Jira/etc. connect mutations). Required for any compliance or IT-admin agent.

## Other capabilities the MCP doesn't expose

Worth knowing about but lower priority:

- **Bulk:** `issueBatchCreate`, `issueBatchUpdate`, `notificationArchiveAll`
- **Issue labels:** full CRUD (MCP has create only)
- **Project milestones / project status:** richer than MCP's milestone tools
- **Project & initiative updates:** separate mutation families MCP doesn't reach
- **Roadmaps:** `roadmapCreate/Update/Delete`, project linkers
- **Git automation:** PR-driven workflow rules
- **Document version history:** `documentContentHistory`
- **Customer CRM:** merge, upsert, status, tier mutations
- **Triage + Asks:** `triageResponsibilityCreate/Update/Delete`, Slack Asks intake

## What the API does *not* give you

Worth flagging so nobody plans around them:

- **API key creation/rotation.** UI-only.
- **Time tracking.** Not in the schema.
- **User-defined custom fields.** Not in the schema.
- **SLA configuration mutations.** Read-only via `slaConfigurations`.

## Auth and rate limits

| | Personal API key | OAuth (user) | OAuth (`actor=app`) |
|---|---|---|---|
| Acts as | Owning user | Authorising user | The app itself |
| Rate limit | 5,000 req/hr **and** 3M complexity/hr | ~1,200 req/hr (lower default) | Scales with paid seats |
| Scopes | n/a (full user perms) | read, write, issues:create, comments:create, admin | All except `admin` |
| Use for | Internal scripts, single-user agents | User-installed integrations | Workspace-wide bot |

GraphQL cost is complexity-based, not just request count. 0.1 per scalar, 1 per object, multiplied by pagination size. A query maxes out at 10,000 points. Headers `X-RateLimit-Requests-*` and `X-Complexity` come back on every response — the skill should read them and back off.

## Skill architecture — progressive discovery

The structure that gets the token win:

```
linear-api/
  SKILL.md                    # ~200 lines, loaded on trigger
  references/
    schema-summary.md         # entity model, field hints
    auth.md                   # API key vs OAuth flows
    rate-limits.md            # complexity rules + retry pattern
    common-queries.md         # 10–15 worked examples
    webhooks.md               # subscription mgmt
    mutations-cheatsheet.md   # the gap-five (cycles, relations, etc.)
  scripts/
    linear.py                 # thin GraphQL client
    introspect.py             # on-demand schema fetch for unknown ops
```

The agent only reads SKILL.md on first use. SKILL.md tells it: "for issues use common-queries.md, for webhook setup use webhooks.md, for unknown territory run introspect.py with the entity name." Each reference file is loaded only when the agent needs that surface area. Result: the agent learns Linear lazily, in chunks proportional to the task.

A worked example: agent gets "subscribe me to all P0 issues in the Mobile team." It loads SKILL.md, sees that subscriptions live in webhooks.md *or* notification-subscriptions, reads the smaller reference, composes one mutation, runs it. Total context cost: maybe 600 lines vs. the ~1,500 lines of MCP tool schemas it would otherwise carry every turn.

## Phased rollout

| Phase | Scope | Done when |
|---|---|---|
| **0 — Spike** | API key auth, GraphQL client, one read query, one mutation | Agent can list issues and create one via the skill |
| **1 — Parity** | Cover the MCP surface (issues, projects, comments, docs) via reference files | Agent passes the same prompts MCP handles today |
| **2 — Gap five** | Webhooks, cycles, workflow states, relations, notification subs | The five blockers from above are reachable |
| **3 — Admin & audit** | OAuth `actor=app`, audit log, admin mutations | Skill ready for compliance / IT-admin use cases |
| **4 — Polish** | Rate-limit-aware retry, schema introspection on demand, telemetry | Production-grade |

A spike fits in a day. Phase 1 a week if you copy MCP's behaviour faithfully. Phase 2 is where it earns its keep.

## Risks and trade-offs

- **GraphQL learning curve for the agent.** The skill has to teach query composition, not just call sites. Mitigation: pre-bake 10–15 common operations in `common-queries.md` so the agent only composes from scratch when needed.
- **Schema drift.** Linear ships changes. A skill written against today's schema can rot. Mitigation: ship `introspect.py` so the agent can re-check field availability when a query fails.
- **Auth-flow complexity.** OAuth `actor=app` is more setup than a personal key. Stay on personal keys until phase 3 unless you need multi-user.
- **Rate-limit surprises.** Complexity scoring is non-obvious. A naive `list_issues(first: 250)` with deep nesting can blow the per-query 10k cap. Test against real workspace data before declaring phase 1 done.
- **You lose MCP's tool-call telemetry.** With MCP, the host shows nice tool-use cards. A direct API skill is more opaque — log every mutation for traceability.

## Recommendation

Build it. Two reasons. The token economics matter more as agents grow more capable — context spent on dormant tool definitions is context not spent on reasoning. And the gap five (webhooks, cycle/state mutations, relations, templates, admin) covers the things you'd actually want an autonomous Linear agent to do, none of which MCP can touch today.

Start with phase 0 against a personal API key on a sandbox workspace. If the spike works and the token savings show up, phase 1 follows naturally.

---

*Output produced in accordance with the human-copy skill at /Users/andyspamer/.claude/skills/human-copy — checked for banned vocabulary, sentence-rhythm variation, concrete specifics, and trade-off honesty before delivery.*
