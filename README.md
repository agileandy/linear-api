# linear-api

A Claude Code / Cowork **skill** that lets an agent talk to Linear's GraphQL API directly — instead of carrying ~40 MCP tool schemas in context every turn. The skill loads on demand, reads only the reference file relevant to the current task, and composes queries via a thin Python CLI.

See `Linear-API-Integration-Plan.md` for the design rationale and gap analysis vs the Linear MCP.

## Status

- **Phase 0 (spike)**: scaffolded — `scripts/linear.py` CLI runs `query` / `mutation` / `introspect`. Awaiting live API key for end-to-end smoke test.
- **Phase 1 (MCP parity)**: not started.
- **Phase 2 (gap five — webhooks, cycles/states, relations, templates, admin)**: not started.
- **Phase 3+ (OAuth `actor=app`, polish)**: deferred.

## Quick start

```bash
uv sync                       # install httpx, python-dotenv, pytest, respx
cp .env.example .env          # then paste your Linear personal API key
uv run python scripts/linear.py query 'query { viewer { id name email } }'
```

### Get a Linear API key

Linear → **Settings → API → Personal API keys → Create key**. Copy the `lin_api_…` token into `.env` as `LINEAR_API_KEY`. The token grants the same permissions as your user account, so use a sandbox workspace for development.

## CLI

```text
linear.py query <doc> [--variables JSON|@file.json]
linear.py mutation <doc> [--variables JSON|@file.json]
linear.py introspect <TypeName>
```

`<doc>` is either an inline GraphQL string or a path to a `.graphql` file.
Rate-limit and complexity headers are written to **stderr** after every call.

## Tests

```bash
uv run pytest                 # mocked — never touches Linear
```

## Layout

```
linear-api/
├── SKILL.md                 # (todo) entry point loaded by the agent
├── references/              # (todo) per-domain cheat sheets
├── scripts/
│   ├── linear.py            # GraphQL CLI
│   └── examples/
│       └── list_my_issues.py
└── tests/
    └── test_linear_client.py
```
