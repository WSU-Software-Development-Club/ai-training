# Frontend

A **React 18.2 SPA** built with Create React App (`react-scripts` 5), routed with
**react-router-dom 7.9.4**, Node 18. No Redux/Context store, no CSS-in-JS/UI kit — local
state + module caches + CSS Modules.

- Source: [`frontend/src/`](../frontend/src/)
- Onboarding walkthrough: [`frontend_guide.md`](../frontend_guide.md)
- Deps of note: `papaparse` (team CSV), `react-icons/fi` (Feather icons).

## Entry & routing

- `src/index.js` — mounts `<App />` into `#root` (`React.StrictMode`), imports global `index.css`.
- `src/App.jsx` — `<BrowserRouter>` wrapping:
  - `RoutePrefetcher` — calls `prefetchForRoute(pathname)` on every location change (renders nothing).
  - `<Header>` rendered **once outside `<Routes>`** so it survives navigation (avoids nav/logo remount flicker — commit `f8bab72`).
  - `AnimatedRoutes` — keys a `.pageFade` wrapper on `location.pathname` to replay the route-transition fade.
  - On mount: `preloadTeamData()` (branding CSV) + a best-effort `api.getHealthStatus()` ping.

**Route table:**

| Path | Component |
| --- | --- |
| `/` | `HomePage` |
| `/rankings` | `RankingsPage` |
| `/stats` | `StatsPage` |
| `/teams` | `TeamsPage` |
| `/comparison` | `ComparisonPage` |
| `/prediction` | `PredictionPage` |
| `/team/:teamName` | `TeamPage` |
| `/matchup/:gameId` | `MatchupPage` |

The nav bar (`Navigation.jsx`) links the six top-level tabs; `/team/:teamName` and
`/matchup/:gameId` are **link-only** (reached from cards/tables, not the tab bar).

> **Dead code:** `src/pages/ScoresPage.jsx` is not registered in any route, renders its own
> duplicate `<Header>`, and reads `utils/mockData.js` — a pre-API-integration draft
> superseded by `HomePage`. Candidate for removal.

## Pages (`src/pages/`)

| Page | Route | What it does |
| --- | --- | --- |
| `HomePage` | `/` | Weekly scoreboard grid (`ScoreCard` per game), grouped by date; filters year/week/conference/status/date. Persists `{conference,status,week,year}` to `sessionStorage` (`homeFilters`; date excluded). Instant render via `peekScoreboardByWeek`, falls back to the network fetch. |
| `RankingsPage` | `/rankings` | AP Top 25 via `getRankings()` → `RankingsTable`. |
| `StatsPage` | `/stats` | Category dropdown driving `getStats`/`peekStats`; mock fallback for categories without backend support. → `StatsTable`. |
| `TeamsPage` | `/teams` | Full team list via `getAllTeams()`, grouped by conference, client-side sortable. |
| `TeamPage` | `/team/:teamName` | Single-team detail via `getTeamData(teamName)`; branding via `useTeamBranding`. |
| `ComparisonPage` | `/comparison` | Two team dropdowns, independent `getTeamData()` fetches; selection persisted to `sessionStorage` + `?teamA=&teamB=` support. |
| `PredictionPage` | `/prediction` | Week/year picker over the scoreboard, filtered to games with a model prediction; `PredictionCard` per game + accuracy summary; links to `/matchup/:ncaaGameId`. |
| `MatchupPage` | `/matchup/:gameId` | The Matchup Intelligence factor board (see below). |

### MatchupPage
Fetches `api.getMatchup(gameId)`; state machine `loading | ready | empty | error` (a **404 →
`empty`**, expected because most games have no deck yet). Renders:
- **`WeatherRow`** — one shared weather condition band above the columns; `WeatherSide` (away/home) shows the team's historical rate deviation vs. baseline (`ppDelta`), record, `n=`, a **thin** flag when withheld or `n < 30`, and the market line inline.
- **`teamsGrid`** of **`TeamFactorDeck`** per team — betting posture (`BettingPosture`) + factors split into `EdgeGroup`s (*Working for them* / tailwind, *Working against them* / headwind). Each non-weather factor is an expandable **`FactorCard`** (category + direction badge, magnitude meter, and on expand the `sources[]` with relative publish times).
- **`ReferencePanels`** — model / Vegas / Polymarket, framed as reference, not the verdict.

See [Matchup Intelligence Engine](matchup-intelligence.md) for the data behind this page.

## Components (`src/components/`)

- **Chrome:** `Header` (branding + `SearchBar` + `Navigation`), `Navigation` (tab bar with an animated sliding highlight tracking `location.pathname`).
- **Search:** `SearchBar` — team autocomplete (loads all teams, client-side filter, keyboard nav, falls back to `matching/teamMatcher.js`).
- **Cards:** `ScoreCard` (game card: scores/O-U/status, team-color styling, "Matchup intel" button → `/matchup/:ncaaGameId`), `TeamCard`, `StatusCard`.
- **Tables:** `RankingsTable` (AP rows, strips the `"(66)"` vote suffix on click), `StatsTable` (dynamic columns driven by whatever keys the stat payload returns).
- **Branding/feedback:** `TeamLogo` (light/dark variant, colored-initial fallback), `LoadingSpinner`.

## API layer (`src/services/api.js`)

All network access goes through this module. Add new endpoints to
`constants/index.js` `appConfig.endpoints` and expose a method on the `api` object — never
`fetch` directly from a component.

- `fetchWithTimeout(url, opts, timeout=90000)` — `AbortController`-based; bridges a caller `signal` (unmount cancellation) and turns a timeout into `Error("Request timeout")`.
- `fetchWithRetry(url, opts, retries=3, timeout=90000)` — retries only `RETRYABLE_STATUS = {408,425,429,500,502,503,504}` + transient network errors with exponential backoff (cap 10s); **never retries a 404** (fails fast).
- `responseCache` — session-lifetime `Map` keyed by URL; caches GETs where `success !== false`; health endpoint excluded. `peekCache(endpoint)` gives zero-flash synchronous renders; `clearApiCache()` resets.
- `apiRequest(endpoint, opts)` — the single `fetch` caller; `url = appConfig.apiUrl + endpoint`.
- `api` methods: `getWelcomeMessage`, `getHealthStatus`, `getStats`/`peekStats`, `getRankings`, `getScoreboardByWeek`/`peekScoreboardByWeek`, `getTeamData`, `getAllTeams`, **`getMatchup(ncaaGameId)`** (→ `/matchup/{id}`; 404 = no deck yet, treat as empty).
- `appConfig.apiUrl = process.env.REACT_APP_API_URL || "http://localhost:5000"`.

## State, data & caching

- **No global store.** Each page owns `useState`/`useEffect` + an `AbortController`-cancelled fetch.
- **`sessionStorage`:** `homeFilters` (HomePage), `comparison.selectedTeamA/B` (ComparisonPage).
- **Team branding** (not from the API): `public/cfb_teams.csv` → `data/csvLoader.js` (PapaParse) → `data/teamDataService.js` (module cache; `preloadTeamData()` on boot) → `branding/teamBranding.js` → `matching/teamMatcher.js` (5-strategy name-match cascade) → `hooks/useTeamBranding.js` (seeds synchronously to avoid a flash of unstyled branding).
- **`services/prefetchService.js`** — `prefetchForRoute(pathname)` runs at `requestIdleCallback` priority, sequentially (never floods the backend): Tier 2 = rest of the current tab's data (once per tab), Tier 3 = defaults for other tabs (once globally). All writes land in the same `api.js` `responseCache`, so pages render instantly via `peekCache`.

## Styling

- **CSS Modules** everywhere (`src/styles/{components,pages}/*.module.css`, imported as `styles`, referenced `styles.xxx`).
- **`src/index.css` is the design-system source of truth** — the "Electric Night" dark theme tokens: `--color-primary`/`--color-accent` `#f43f5e` (electric crimson), `--color-highlight` `#22d3ee` (cyan, for model/prediction data), the `--color-background` ramp, spacing/type/radius/shadow scales, `--ease-smooth`, `.pageFade`, `prefers-reduced-motion` overrides. Dark-only (no theme toggle).

> **Legacy token drift:** `src/constants/{colors,spacing,css}.js` are stale JS mirrors (still
> the old React-blue palette, not the crimson/cyan tokens). `index.css`'s own comment marks
> them legacy/unused — don't treat them as current. Style via `var(--…)` in CSS Modules.

## Config / env

- `REACT_APP_API_URL` — build-time CRA var read once in `constants/index.js`; falls back to `http://localhost:5000`. Set at Vercel build time to the troyster tunnel URL. Never hardcode a base URL elsewhere.

## Gotchas

- **Stale "Render spin-up" rationale** — `fetchWithRetry`'s 90s timeout / 3 retries and the `App.jsx` "Backend warming up…" health ping date from Render's cold starts. The backend is now always-on on troyster; the wrapper is harmless but the comments mislead (CLAUDE.md §7 gotcha 2).
- **Duplicated stat map** — `STAT_NAME_TO_ID` (api.js) must mirror `backend/api_vars.py` `STAT_CATEGORIES` by hand (casing differs); also touch `utils/appData.js` `statCategories` and `utils/mockData.js` `mockStats` when adding a stat.
- **MatchupPage 404** — `apiRequest` throws a generic `Error("HTTP error! status: 404")`; the page string-matches `"404"` to route it to the empty state. A structured error shape would be cleaner.
- **Dead code / legacy tokens** — `ScoresPage.jsx` and `constants/{colors,spacing,css}.js` (above).
