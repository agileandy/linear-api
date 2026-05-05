# Auth

> **Index** — [Personal API key](#personal-api-key) · [OAuth (user)](#oauth-user) · [OAuth actor=app](#oauth-actorapp) · [Header format](#header-format) · [Scope cheatsheet](#scope-cheatsheet) · [Revocation](#revocation)

Linear supports three auth flows. **Use a personal API key for everything until you have a concrete reason not to** — it's the simplest path and matches the workflow this skill is built for.

## Personal API key

| | |
|---|---|
| Acts as | The owning user (full perms of that account) |
| Get one | Linear UI → **Settings → API → Personal API keys → Create key** |
| Token format | `lin_api_…` (48 chars at time of writing) |
| Header | `Authorization: lin_api_…` (raw, **no `Bearer ` prefix**) |
| Rotation | UI-only. The API has no `apiKeyCreate` / `apiKeyRotate` mutation. |
| When to use | Internal scripts, single-user agents, dev / sandbox |
| When not to | Multi-user products, anything you'll ship to a customer |

Storage: drop the token into `.env` as `LINEAR_API_KEY=…`. The CLI loads it via `python-dotenv`. The `.env` file is gitignored; never commit a key.

## OAuth (user)

| | |
|---|---|
| Acts as | The user who completed the OAuth flow |
| Token format | `lin_oauth_…` (or a JWT-shaped access token) |
| Header | `Authorization: Bearer lin_oauth_…` |
| Rate limit | Lower default than personal keys (~1,200 req/hr per user) |
| When to use | A multi-user app where each user authorises against their own data |

The `auth_header()` helper in `scripts/linear.py` switches automatically: tokens starting with `lin_oauth_` get a `Bearer ` prefix; raw `lin_api_…` keys do not.

Skill defers full OAuth wiring to **Phase 3**. Until then, treat OAuth as a TODO.

## OAuth actor=app

The interesting flavour for autonomous agents. The app acts as **itself** rather than as a specific user — comments, issues, and webhooks are attributed to the app's name, not whichever user installed it.

| | |
|---|---|
| Acts as | The app (workspace-wide, not user-scoped) |
| Token format | OAuth access token with `actor=app` parameter set during the flow |
| Scopes | Everything except `admin` |
| Rate limit | Scales with the workspace's paid seat count |
| When to use | A workspace-wide bot (Linear's reference example: "the agent that triages issues") |
| Setup cost | Higher — needs a registered OAuth app, redirect URI, secret rotation |

Reference: <https://linear.app/developers/oauth-actor-authorization>

## Header format

```http
POST /graphql HTTP/1.1
Host: api.linear.app
Content-Type: application/json
Authorization: lin_api_xxxxxxxx                # personal key, raw
# OR
Authorization: Bearer lin_oauth_xxxxxxxx       # OAuth user token
# OR
Authorization: Bearer eyJhbGciOi…              # OAuth actor=app JWT
```

`scripts/linear.py auth_header()` handles all three. The unit tests cover each branch.

## Scope cheatsheet

OAuth flows let you request a subset of permissions. Personal keys are full-power and do not use scopes.

| Scope | Grants |
|---|---|
| `read` | Read access to all resources (issues, projects, comments, etc) |
| `write` | Read + create/update/delete on most resources |
| `issues:create` | Create issues only — useful for narrow integrations |
| `comments:create` | Create comments only |
| `admin` | Workspace admin surface (user roles, billing, integrations). **Not granted to actor=app.** |

## Revocation

- **Personal key:** delete it in the UI (Settings → API → Personal API keys → trash icon). Effective immediately.
- **OAuth token:** call `revokeUser` mutation (user-scoped) or have the user uninstall the app from Settings → Apps.
- **If a key leaks:** revoke first, then regenerate. There is no "rotate" endpoint — revoke + recreate is the only path.

If you suspect a key in this repo's history was committed by mistake, the answer is the same: revoke it in Linear, regenerate, then strip from git history with `git filter-repo` or BFG. Don't try to "fix it later."
