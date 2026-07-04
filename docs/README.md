# Documentation

Comprehensive reference documentation for the **CFB Analytics & Predictions** app —
a college-football analytics and predictions web app (React SPA + Flask JSON API +
offline ML pipeline) built by the WSU Software Development Club and deployed at
**https://football.wsu-swdc.dev**.

> New here? Start with **[Architecture](architecture.md)** for the big picture,
> then **[Development](development.md)** to run it locally.

## Contents

| Doc | What's inside |
| --- | --- |
| [Architecture](architecture.md) | System overview, the three subsystems, request/data flow, deployment topology at a glance. |
| [Development](development.md) | Local setup (Docker + individual services), env vars, running tests, the ML pipeline locally. |
| [Backend API](backend-api.md) | Flask app-factory, every route/blueprint, response envelope, services & utilities. |
| [Frontend](frontend.md) | React SPA structure — pages, components, the API layer, state/caching, styling tokens. |
| [ML — Score Predictions](ml-predictions.md) | The XGBoost home/away score models: training, weekly prediction job, the `predictions` contract. |
| [Matchup Intelligence Engine](matchup-intelligence.md) | The factor-deck subsystem: ingest → extract → ground → score → serve, and its three hard guarantees. |
| [Database](database.md) | Full `db/schema.sql` reference — every table, the two id spaces, the schema-change protocol. |
| [Deployment & Operations](deployment.md) | troyster + Vercel + Cloudflare Tunnel topology, Docker Compose, the three CI/CD workflows, secrets. |
| [Known Issues & Tech Debt](known-issues.md) | Running register of tech debt, drift, and dead code, with locations and suggested fixes. |

## The system in one paragraph

A **React SPA** (hosted on Vercel) talks to a **Flask JSON API** (self-hosted on
the `troyster` homelab node behind a Cloudflare Tunnel). The API proxies live NCAA
data (rankings, stats, scoreboards) and serves model output stored in a self-hosted
**Postgres** database. Two offline pipelines feed that database: the **score-prediction
models** (XGBoost, retrained/predicted weekly via GitHub Actions) and the **Matchup
Intelligence Engine** (per-game scored, sourced factor decks). See
[Architecture](architecture.md) for how the pieces fit together.

## Related docs

These onboarding guides live at the repo root and predate this `/docs` set — they go
deeper on their topics and remain valid:

- [`../CLAUDE.md`](../CLAUDE.md) — the canonical project/agent context file (stack, topology, conventions, gotchas).
- [`../backend_guide.md`](../backend_guide.md) — backend onboarding walkthrough.
- [`../backend_route_testing_guide.md`](../backend_route_testing_guide.md) — how to test routes.
- [`../frontend_guide.md`](../frontend_guide.md) — frontend onboarding walkthrough.
- [`../github_guide.md`](../github_guide.md) — GitHub / CI workflow guide.
- [`../.claude/agents/README.md`](../.claude/agents/README.md) — the project's Claude Code subagents.
