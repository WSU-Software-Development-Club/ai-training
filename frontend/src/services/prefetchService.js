/**
 * Prefetch Service
 *
 * Warms the session response cache (see `api.js`) in the background so that
 * navigating between weeks/tabs feels instant. It runs in three tiers, in
 * priority order:
 *
 *   Tier 1 (handled by each page itself): the current selection of the current
 *           page — e.g. the current week's scoreboard on Home. Not done here.
 *   Tier 2 (this service): the *rest* of the data for the tab the user is on —
 *           e.g. every other week on Home, every other stat category on Stats.
 *   Tier 3 (this service): the default selection for every *other* tab, so the
 *           first paint of any tab the user clicks into is already cached.
 *
 * All prefetching happens at idle priority and sequentially, so it never
 * competes with the user's active navigation or floods the backend. Prefetch
 * failures are intentionally swallowed — the real page fetch will retry and
 * surface errors when the data is actually needed.
 */

import api, { getStats, hasBackendSupport } from "./api";
import { getCurrentWeek, getCurrentYear } from "../utils/helpers";
import { statCategories } from "../utils/appData";

// Matches the week range used by HomePage's dropdown.
const TOTAL_WEEKS = 19;

// Matches StatsPage's initial `selectedCategory`.
const DEFAULT_STAT_CATEGORY = "Total Offense";

const allWeeks = () => Array.from({ length: TOTAL_WEEKS }, (_, i) => i + 1);

// Schedule low-priority work without blocking the current render/navigation.
const scheduleIdle = (cb) => {
  if (
    typeof window !== "undefined" &&
    typeof window.requestIdleCallback === "function"
  ) {
    window.requestIdleCallback(cb, { timeout: 3000 });
  } else {
    setTimeout(cb, 300);
  }
};

// Fire a request purely to populate the session cache. Errors are swallowed so
// a failed prefetch never surfaces to the user.
const warm = (task) =>
  Promise.resolve()
    .then(task)
    .catch(() => {});

// Run tasks one at a time so we never flood the backend with a burst of
// parallel prefetch requests competing with the user's real navigation.
async function runSequentially(tasks) {
  for (const task of tasks) {
    await warm(task);
  }
}

// The default ("landing") request for each tab — what that page loads on mount.
// Home passes the current year so the cache key matches HomePage's request
// (which always includes ?year=...).
const defaultTaskByTab = {
  "/": () => api.getScoreboardByWeek(getCurrentWeek(), getCurrentYear()),
  "/stats": () => getStats(DEFAULT_STAT_CATEGORY),
  "/rankings": () => api.getRankings(),
  "/teams": () => api.getAllTeams(),
  "/comparison": () => api.getAllTeams(),
};

// Builders for the remaining ("non-default") data for a given tab. Tabs whose
// data is a single dataset (Rankings, Teams, Comparison) have nothing extra to
// prefetch beyond their default, so they're omitted.
const restTasksByTab = {
  "/": () =>
    allWeeks()
      .filter((week) => week !== getCurrentWeek())
      .map((week) => () => api.getScoreboardByWeek(week, getCurrentYear())),
  "/stats": () =>
    statCategories
      .filter(
        (category) =>
          category !== DEFAULT_STAT_CATEGORY && hasBackendSupport(category)
      )
      .map((category) => () => getStats(category)),
};

// Track what we've already kicked off so repeated navigation doesn't relaunch
// prefetch passes. (The cache would dedupe the network anyway, but this avoids
// rebuilding and re-queueing the task lists unnecessarily.)
const restPrefetchedTabs = new Set();
let defaultsPrefetched = false;

/**
 * Kick off background prefetching appropriate for the given route.
 *
 * @param {string} pathname - The current route pathname (e.g. "/", "/stats")
 */
export function prefetchForRoute(pathname) {
  scheduleIdle(async () => {
    // Tier 2: finish loading the rest of the current tab's data.
    const buildRest = restTasksByTab[pathname];
    if (buildRest && !restPrefetchedTabs.has(pathname)) {
      restPrefetchedTabs.add(pathname);
      await runSequentially(buildRest());
    }

    // Tier 3: warm the default data for every other tab. The current tab's own
    // default is already loaded by the page itself (tier 1), so skip it.
    if (!defaultsPrefetched) {
      defaultsPrefetched = true;
      const otherDefaults = Object.entries(defaultTaskByTab)
        .filter(([tab]) => tab !== pathname)
        .map(([, task]) => task);
      await runSequentially(otherDefaults);
    }
  });
}

// Exposed for tests / manual cache resets.
export function resetPrefetchState() {
  restPrefetchedTabs.clear();
  defaultsPrefetched = false;
}
