# Project subagents

Specialized [Claude Code subagents](https://docs.claude.com/en/docs/claude-code/sub-agents) for this repo. Because they live in `.claude/agents/`, they're shared with everyone who clones the project — Claude Code auto-discovers them, and you can invoke one explicitly (e.g. "use the `aitraining-frontend` agent to …") or let Claude route to it.

Each file is a Markdown doc with YAML frontmatter (`name`, `description`, `tools`, `model`) and a system prompt body. Edit the body to change how an agent behaves.

## The team

**Layer specialists** — scoped to one part of the stack:
- `aitraining-backend` — Flask routes/services/CORS/Postgres reads
- `aitraining-frontend` — React SPA pages/components/API integration
- `aitraining-ml` — the XGBoost score-prediction pipeline under `ml/`
- `aitraining-db-migration` — `db/schema.sql` + query correctness
- `aitraining-infra` — docker-compose/Dockerfiles, Cloudflare tunnel, troyster deploy

**Quality & review** (read-only unless noted):
- `aitraining-code-reviewer` — prioritized findings on a diff/file
- `aitraining-security-scanner` — secrets/exposed-key sweep before a PR
- `aitraining-api-contract` — frontend↔backend + duplicated stat-map drift
- `aitraining-test-runner` — runs suites, reports only failures
- `aitraining-test-author` — writes pytest / RTL tests
- `aitraining-debugger` — root-causes a trace/failing test
- `aitraining-refactor` — structural, behavior-preserving edits

**Direction & docs** (read-only advisors):
- `aitraining-product-manager` — turns vague goals into a sequenced roadmap
- `aitraining-feature-scout` — proposes buildable features
- `aitraining-ux-designer` — visual/UX polish (can apply CSS/markup)
- `aitraining-explorer` — "how does X work / where is Y" with file:line pointers
- `aitraining-docs-writer` — README / `*_guide.md` / docstrings / env.example
- `aitraining-context-updater` — reconciles `CLAUDE.md` with the real code
- `aitraining-orchestrator` — coordinates a task spanning multiple layers
- `aitraining-commit-pr` — drafts Conventional Commit messages / PR bodies
- `aitraining-prompt-refiner` — tightens these agent prompts themselves

**Research personas** (stand-in users, not tools):
- `sharp-bettor` — "Sharp", a disciplined CFB bettor you interview to pressure-test matchup-tool features and mockups. Reacts as a target user; never gives picks.

## Notes

- Machine-local overrides in `~/.claude/agents/` with the same filename take precedence over these; delete the personal copies if you want the repo version to be the single source of truth.
- `settings.local.json` in this directory is intentionally gitignored (per-machine); these agent files are not.
