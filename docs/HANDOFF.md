# Handoff Brief — Build the Linear API Skill

You are receiving this from a Claude desktop session. Andy (Agile Coach / Tech Delivery Lead) wants you to build a Linear API integration as a **Claude Code / Cowork skill** that uses progressive discovery instead of MCP. The token-efficiency case and gap analysis are in the companion file `Linear-API-Integration-Plan.md` (already copied into this folder). Read it first.

## Tech stack (already chosen)

- **Python 3.11+** with `httpx` (async-capable, modern HTTP client)
- **`python-dotenv`** for API key loading
- **No GraphQL client library** — hand-rolled queries keep the skill files small and easy for an agent to inspect. Pure dict → JSON → POST.
- **No build step**. Scripts run as `python3 scripts/linear.py ...`. This matches the Anthropic skill pattern.
- **Optional:** `pytest` for the verification suite.

## Repository layout to build

```
linear-api/
├── README.md                       # what this is, how to install as a skill
├── pyproject.toml                  # deps: httpx, python-dotenv, pytest
├── .env.example                    # LINEAR_API_KEY=lin_api_xxx
├── .gitignore                      # .env, __pycache__, .venv, etc.
├── SKILL.md                        # the skill entry point (loaded by agent)
├── references/
│   ├── schema-summary.md           # entity model, key fields per type
│   ├── auth.md                     # API key vs OAuth flows + how to get a key
│   ├── rate-limits.md              # complexity rules, retry pattern, headers
│   ├── common-queries.md           # 10–15 worked GraphQL examples
│   ├── webhooks.md                 # webhook subscription mgmt
│   └── mutations-cheatsheet.md     # the gap five (cycles, relations, states, templates, admin)
├── scripts/
│   ├── linear.py                   # thin GraphQL client (CLI: query / mutation / introspect)
│   ├── introspect.py               # on-demand schema fetch for unknown types
│   └── examples/
│       ├── list_my_issues.py
│       ├── create_issue.py
│       └── subscribe_webhook.py
└── tests/
    └── test_linear_client.py       # mock-based unit tests (don't hit prod)
```

## Phase 0 — Spike (do this first, get it working end-to-end)

1. Init repo: `git init`, `pyproject.toml`, virtualenv, `.gitignore`.
2. Build `scripts/linear.py` as a CLI:
   - Reads `LINEAR_API_KEY` from `.env`.
   - Subcommands: `query <file-or-string>`, `mutation <file-or-string>`, `introspect <type>`.
   - Posts to `https://api.linear.app/graphql`.
   - Prints `X-RateLimit-Requests-Remaining` and `X-Complexity` to stderr after every call.
   - Pretty-prints the response JSON.
3. Smoke test: `viewer { id name email }` query against Andy's workspace.
4. Smoke test: create a throwaway issue in a sandbox team and delete it.
5. Commit phase 0 working spike.

## Phase 1 — MCP parity surface

Cover what the MCP exposes so the skill is a drop-in for existing workflows. Build out `references/common-queries.md` and example scripts for: issues (list/get/save), projects, comments, documents, attachments, teams, users, labels, milestones, initiatives, status updates, customers.

## Phase 2 — The gap five (the reason this exists)

Build out `references/webhooks.md` and `references/mutations-cheatsheet.md` covering:

1. **Webhooks CRUD** — `webhookCreate / Update / Delete / RotateSecret`
2. **Cycle + workflow-state mutations** — `cycleCreate/Update/Archive/ShiftAll/StartUpcomingCycleToday`, `workflowStateCreate/Update/Archive`
3. **Issue relations, reactions, notification subscriptions** — `issueRelationCreate/Update/Delete`, `reactionCreate/Delete`, `notificationSubscriptionCreate/Update/Delete`
4. **Templates, custom views, favorites** — `templateCreate/Update/Delete`, `customViewCreate/Update/Delete`, `favoriteCreate/Update/Delete`
5. **Audit log + admin surface** — `auditEntries` query, `userChangeRole/Suspend/Unsuspend`, `organizationInvite*`, integration mutations

## Phase 3+ — defer

OAuth `actor=app` flow, polish, telemetry. Don't do this in the first build. Note as TODO in README.

## SKILL.md design (this is the headline win)

The whole point of this project is token efficiency. SKILL.md must be **lean** (~150-200 lines max). It should:

- Tell the agent in 3 sentences what Linear is and what this skill does.
- List the reference files with one-line summaries so the agent knows which to load for which task.
- Include a 10-line "first-run" checklist (auth, smoke test).
- Show ONE worked example end-to-end so the agent gets the pattern.
- **Not** dump every mutation/query — that's what the references are for.

The agent should only load reference files relevant to the task at hand. If asked to manage a webhook, it loads `webhooks.md`, not `common-queries.md`.

## Quality bar

- Every script handles the rate-limit headers and exits cleanly on 429.
- Every reference file has a top-of-file index so the agent can scan-then-load.
- `README.md` includes: how to get a Linear API key, how to install as a Claude Code skill, how to run tests.
- `tests/test_linear_client.py` mocks `httpx` — never hits Linear in CI.
- Commits should be granular and well-messaged.

## Sources to consult

- https://linear.app/developers/graphql
- https://linear.app/developers/rate-limiting
- https://linear.app/developers/webhooks
- https://linear.app/developers/oauth-actor-authorization
- https://github.com/linear/linear/blob/master/packages/sdk/src/schema.graphql

## Operating instructions for this session

You are running with `--dangerously-skip-permissions`. Andy has approved this. Work autonomously through phase 0 and phase 1 without asking for permission on routine operations (file writes, package installs, git operations). Stop and ask only when:

- You hit a credential blocker (Andy needs to give you a Linear API key for live testing).
- You're about to do something destructive outside this folder.
- A design decision genuinely needs his input (don't make these up).

When phase 0 spike is working, **stop and report back**. Andy will provide a real API key for the live smoke test, then you continue through phase 1.

Begin by:
1. `cat Linear-API-Integration-Plan.md` to get the full context.
2. Confirm Python 3.11+ is available; create `.venv`.
3. Scaffold the project layout above.
4. Build phase 0.

Good luck.
