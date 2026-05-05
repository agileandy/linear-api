# linear-api

A Claude Code / Cowork **skill** that lets an agent talk to Linear's GraphQL API directly — instead of carrying ~40 MCP tool schemas in context every turn. The skill loads on demand, reads only the reference file relevant to the current task, and composes queries via a thin Python CLI.

See `Linear-API-Integration-Plan.md` for the design rationale and the gap analysis against the Linear MCP. The lean entry point an agent reads on first use is `SKILL.md`.

## Status

- **Phase 0 (spike)** — ✅ done. CLI live-tested against a real workspace (`viewer`, issue create → soft-delete → hard-delete → verify, type introspection). Findings in `references/rate-limits.md`.
- **Phase 1 (MCP parity)** — ✅ done. Lean `SKILL.md`, foundational references (`auth`, `schema-summary`, `rate-limits`, `common-queries`), and three pattern-focused example scripts. The `common-queries.md` reference covers the full MCP surface: issues, comments, projects, initiatives, milestones, cycles, teams, users, labels, documents, attachments, customers, customer needs, status updates, project labels.
- **Phase 2 (gap five — webhooks, cycles/states, relations, templates, admin)** — ✅ done. `references/webhooks.md` covers the full subscription surface (resource types, signing, delivery semantics, common pitfalls). `references/mutations-cheatsheet.md` covers cycle + workflow-state CRUD, issue relations + reactions + notification subscriptions, templates + custom views + favorites, and the audit log + admin / org / integration management surface. Plus `scripts/examples/subscribe_webhook.py`.
- **Phase 3+ (OAuth `actor=app`, polish, retry helpers)** — backlog tracked in Linear:
  - **[AGI-87](https://linear.app/agileandy/issue/AGI-87)** — OAuth `actor=app` flow
  - **[AGI-88](https://linear.app/agileandy/issue/AGI-88)** — rate-limit-aware retry helper
  - **[AGI-89](https://linear.app/agileandy/issue/AGI-89)** — schema introspection cache
  - **[AGI-90](https://linear.app/agileandy/issue/AGI-90)** — structured mutation logging / telemetry

## Quick start

```bash
uv sync                       # installs httpx, python-dotenv, pytest, respx
cp .env.example .env          # then paste your Linear personal API key
uv run python scripts/linear.py query 'query { viewer { id name email } }'
```

### Get a Linear API key

Linear → **Settings → API → Personal API keys → Create key**. Copy the `lin_api_…` token into `.env` as `LINEAR_API_KEY`. The token grants the same permissions as your user account, so use a sandbox workspace for development. See `references/auth.md` for OAuth flows (Phase 3).

## Install as a Claude Code skill

This repo is structured as a Claude Code skill — an `SKILL.md` entry point, on-demand `references/`, and a CLI under `scripts/`. To make it discoverable to Claude Code:

```bash
# Project-scoped install (visible only inside this project)
mkdir -p .claude/skills
ln -s "$(pwd)" .claude/skills/linear-api

# Or global install (visible across every project)
mkdir -p ~/.claude/skills
ln -s "$(pwd)" ~/.claude/skills/linear-api
```

When Claude Code starts in a project that can see this skill, it surfaces the `name` and `description` from `SKILL.md`'s frontmatter. The agent loads `SKILL.md` only on first use; the per-domain reference files load only when a task touches that surface. That progressive-discovery pattern is the whole point — it's why this is cheaper in tokens than the Linear MCP.

`LINEAR_API_KEY` must be available in the environment when the skill runs. Either keep it in this project's `.env`, or export it from your shell profile.

## CLI

```text
linear.py query     <doc-or-file> [--variables JSON|@file.json]
linear.py mutation  <doc-or-file> [--variables JSON|@file.json]
linear.py introspect <TypeName>
```

`<doc-or-file>` is either an inline GraphQL string or a path to a `.graphql` file.
Rate-limit (`x-ratelimit-*`) and complexity (`x-complexity`) headers are written to **stderr** after every call. The CLI raises and exits non-zero on HTTP 429 with `retry-after` in the message — see `references/rate-limits.md` for the retry pattern.

## Example scripts

```bash
uv run python scripts/examples/list_my_issues.py
uv run python scripts/examples/create_issue.py --team-key AGI --title "..." --priority 2
uv run python scripts/examples/paginate_issues.py --team-key AGI
uv run python scripts/examples/subscribe_webhook.py --url https://your-receiver.example.com/linear \
  --label "triage agent" --resource-types Issue Comment --team-key AGI
```

These exist to demonstrate **patterns** (read, write-then-read, cursor pagination), not to enumerate every possible operation. For breadth, load `references/common-queries.md`.

## Tests

```bash
uv run pytest                 # mocked via respx — never touches Linear
```

13 mock tests cover the GraphQL transport, header logging, auth-mode switching, and the 429 / GraphQL-error paths.

## Layout

```
linear-api/
├── SKILL.md                          # lean entry point — loaded by the agent on first use
├── README.md                         # this file
├── HANDOFF.md                        # original build brief (preserved for context)
├── Linear-API-Integration-Plan.md    # design rationale + MCP gap analysis
├── pyproject.toml
├── .env.example
├── references/
│   ├── auth.md                       # personal key vs OAuth, scopes, revocation
│   ├── schema-summary.md             # entity model, identifiers, pagination, soft/hard delete
│   ├── rate-limits.md                # observed limits, complexity examples, retry pattern
│   ├── common-queries.md             # 18 worked GraphQL ops — full MCP-parity surface
│   ├── webhooks.md                   # webhook subscription mgmt (resource types, signing, delivery)
│   └── mutations-cheatsheet.md       # the gap five — cycles, states, relations, templates, admin
├── scripts/
│   ├── linear.py                     # GraphQL CLI
│   └── examples/
│       ├── list_my_issues.py
│       ├── create_issue.py
│       ├── paginate_issues.py
│       └── subscribe_webhook.py
└── tests/
    └── test_linear_client.py         # respx-mocked unit tests
```

## Why a skill instead of the MCP

Three reasons, in order:

1. **Coverage.** The Linear MCP can't manage webhooks, cycle/state mutations, issue relations, templates, custom views, audit log, or admin surface. The API can. That gap is the reason this project exists — see Phase 2.
2. **Token cost.** The MCP loads ~40 tool schemas into the agent's context every turn, whether the agent touches Linear or not. This skill loads `SKILL.md` (~120 lines) on trigger, then *only* the one reference file the task needs.
3. **Control.** GraphQL only returns the fields you ask for. No fixed tool shapes — if you need a field the MCP doesn't expose, you ask for it.

The trade-off is that the agent has to learn query composition rather than calling pre-baked tools. `references/common-queries.md` is the one-time price for that — 15 worked examples that cover the MCP-parity surface so the agent only composes from scratch when it goes off-piste.
