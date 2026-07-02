import { appConfig } from "../constants";

// Base API configuration
const API_BASE_URL = appConfig.apiUrl;

// HTTP statuses worth retrying: transient server/tunnel/rate-limit errors.
// Client errors (4xx, except the ones below) are not retried — they won't
// succeed on a second attempt.
const RETRYABLE_STATUS = new Set([408, 425, 429, 500, 502, 503, 504]);

// True when a request was cancelled (e.g. the user navigated to another tab).
const isAbortError = (error) => error && error.name === "AbortError";

// Timeout utility - actually aborts the underlying request on timeout, and
// honors an external AbortSignal (from the caller) so navigation can cancel it.
const fetchWithTimeout = async (url, options = {}, timeout = 90000) => {
  const controller = new AbortController();
  let timedOut = false;

  const timeoutId = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeout);

  // Bridge the caller's signal (used to cancel on unmount) to our controller.
  const externalSignal = options.signal;
  const onExternalAbort = () => controller.abort();
  if (externalSignal) {
    if (externalSignal.aborted) {
      controller.abort();
    } else {
      externalSignal.addEventListener("abort", onExternalAbort, { once: true });
    }
  }

  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } catch (error) {
    // A timeout surfaces as an AbortError; convert it to a retryable error so
    // it's distinguishable from a caller-initiated cancellation.
    if (isAbortError(error) && timedOut) {
      throw new Error("Request timeout");
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
    if (externalSignal) {
      externalSignal.removeEventListener("abort", onExternalAbort);
    }
  }
};

// Retry utility with exponential backoff. Retries transient network failures,
// timeouts, and retryable HTTP statuses — but never retries a cancelled
// request or a non-transient client error.
const fetchWithRetry = async (
  url,
  options = {},
  retries = 3,
  timeout = 90000
) => {
  for (let i = 0; i < retries; i++) {
    const isLastRetry = i === retries - 1;

    let response;
    try {
      response = await fetchWithTimeout(url, options, timeout);
    } catch (error) {
      // Caller cancelled (navigation/unmount): bail immediately, don't retry.
      if (isAbortError(error)) {
        throw error;
      }
      if (isLastRetry) {
        throw error;
      }
      await backoff(i);
      continue;
    }

    if (response.ok) {
      return response;
    }

    // Retry transient server errors; fail fast on everything else (e.g. 404).
    if (RETRYABLE_STATUS.has(response.status) && !isLastRetry) {
      await backoff(i);
      continue;
    }

    throw new Error(`HTTP error! status: ${response.status}`);
  }
};

// Exponential backoff helper (2^i seconds, capped at 10s).
const backoff = (attempt) => {
  const waitTime = Math.min(1000 * Math.pow(2, attempt), 10000);
  console.log(
    `Request failed, retrying in ${waitTime}ms... (attempt ${attempt + 1})`
  );
  return new Promise((resolve) => setTimeout(resolve, waitTime));
};

// Session-scoped, in-memory response cache. The API returns small, mostly
// static payloads (rankings, weekly scores, season stats, team lists), so we
// cache successful GET responses for the lifetime of the page. A full page
// reload starts a fresh session and clears everything — this is deliberately
// short-term.
const responseCache = new Map();

// Live/status endpoints that must always hit the network.
const NON_CACHEABLE_ENDPOINTS = [appConfig.endpoints.health];

const isCacheableRequest = (endpoint, method) =>
  method === "GET" &&
  !NON_CACHEABLE_ENDPOINTS.some((e) => e && endpoint.startsWith(e));

// Deep-copy cached values so callers can freely mutate results (sort, etc.)
// without corrupting the shared cache entry.
const cloneData = (data) => {
  if (typeof structuredClone === "function") {
    return structuredClone(data);
  }
  return JSON.parse(JSON.stringify(data));
};

// Clear the session cache (e.g. to force fresh data). Exposed for callers/tests.
export const clearApiCache = () => responseCache.clear();

// Synchronously read an already-cached GET response for an endpoint, or return
// undefined if it hasn't been fetched yet. Lets components render prefetched
// data instantly (no async gap / loading flash) and fall back to a normal
// request when the data isn't cached.
export const peekCache = (endpoint) => {
  const url = `${API_BASE_URL}${endpoint}`;
  if (responseCache.has(url)) {
    return cloneData(responseCache.get(url));
  }
  return undefined;
};

// Generic API request function
const apiRequest = async (endpoint, options = {}) => {
  const url = `${API_BASE_URL}${endpoint}`;
  const method = (options.method || "GET").toUpperCase();
  const cacheable = isCacheableRequest(endpoint, method);

  // Serve previously-received data instantly, without touching the network.
  if (cacheable && responseCache.has(url)) {
    return cloneData(responseCache.get(url));
  }

  const config = {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  };

  try {
    const response = await fetchWithRetry(url, config, 3, 90000);
    const data = await response.json();

    // Only cache genuine successful payloads — never an error-shaped response.
    if (cacheable && data && data.success !== false) {
      responseCache.set(url, data);
      return cloneData(data);
    }

    return data;
  } catch (error) {
    // Cancellations are expected during navigation — not real failures.
    if (!isAbortError(error)) {
      console.error("API request failed:", error);
    }
    throw error;
  }
};

// Stat name to stat ID mapping (matches backend/api_vars.py STAT_CATEGORIES)
const STAT_NAME_TO_ID = {
  "3rd Down Conversion Pct": 699,
  "3rd Down Conversion Pct Defense": 701,
  "4th Down Conversion Pct": 700,
  "4th Down Conversion Pct Defense": 702,
  "Blocked Kicks": 785,
  "Blocked Kicks Allowed": 786,
  "Blocked Punts": 790,
  "Blocked Punts Allowed": 791,
  "Completion Percentage": 756,
  "Defensive TDs": 926,
  "Fewest Penalties": 876,
  "Fewest Penalties Per Game": 697,
  "Fewest Penalty Yards": 877,
  "Fewest Penalty Yards Per Game": 698,
  "First Downs Defense": 694,
  "First Downs Offense": 693,
  "Fumbles Lost": 458,
  "Fumbles Recovered": 456,
  "Kickoff Return Defense": 463,
  "Kickoff Returns": 96,
  "Net Punting": 98,
  "Passes Had Intercepted": 459,
  "Passes Intercepted": 457,
  "Passing Offense": 25,
  "Passing Yards Allowed": 695,
  "Passing Yards per Completion": 741,
  "Punt Return Defense": 462,
  "Punt Returns": 97,
  "Red Zone Defense": 704,
  "Red Zone Offense": 703,
  "Rushing Defense": 24,
  "Rushing Offense": 23,
  "Sacks Allowed": 468,
  "Scoring Defense": 28,
  "Scoring Offense": 27,
  "Tackles for Loss Allowed": 696,
  "Team Passing Efficiency": 465,
  "Team Passing Efficiency Defense": 40,
  "Team Sacks": 466,
  "Team Tackles for Loss": 467,
  "Time of Possession": 705,
  "Total Defense": 22,
  "Total Offense": 21,
  "Turnover Margin": 29,
  "Turnovers Gained": 460,
  "Turnovers Lost": 461,
  "Winning Percentage": 742,
};

// Check if a category has backend support
export const hasBackendSupport = (category) => {
  return STAT_NAME_TO_ID.hasOwnProperty(category);
};

// Build the scoreboard endpoint for a week (with optional year). Shared by the
// async fetch and the synchronous cache peek so their cache keys always match.
const scoreboardEndpoint = (week, year) => {
  let endpoint = appConfig.endpoints.scores + week;
  if (year) {
    endpoint += `?year=${year}`;
  }
  return endpoint;
};

// Build the stats endpoint for a category, or null if unsupported. Shared by
// the async fetch and the synchronous cache peek so their keys always match.
const statsEndpoint = (category) => {
  const statId = STAT_NAME_TO_ID[category];
  return statId ? `/stats/stat/${statId}` : null;
};

// Generic function to get stats for any category
export const getStats = async (category, options) => {
  const endpoint = statsEndpoint(category);
  if (!endpoint) {
    throw new Error(`No backend support for category: ${category}`);
  }
  return apiRequest(endpoint, options);
};

// Synchronously read a cached stat category (or undefined if not cached).
export const peekStats = (category) => {
  const endpoint = statsEndpoint(category);
  return endpoint ? peekCache(endpoint) : undefined;
};

// Specific API functions. Each accepts an optional `options` object (e.g.
// `{ signal }`) so callers can cancel requests when a component unmounts.
export const api = {
  // Get welcome message
  getWelcomeMessage: (options) => apiRequest(appConfig.endpoints.home, options),

  // Get health status
  getHealthStatus: (options) =>
    apiRequest(appConfig.endpoints.health, options),

  // Get stats for any supported category
  getStats,

  // Get AP rankings
  getRankings: (options) => apiRequest(appConfig.endpoints.rankings, options),

  // Get scoreboard by a given week
  getScoreboardByWeek: (week, year, options) =>
    apiRequest(scoreboardEndpoint(week, year), options),

  // Synchronously read a cached scoreboard week (or undefined if not cached).
  peekScoreboardByWeek: (week, year) => peekCache(scoreboardEndpoint(week, year)),

  // Get a given team's current season data
  getTeamData: (team, options) =>
    apiRequest(appConfig.endpoints.team + team + "/record", options),

  // Get all teams
  getAllTeams: (options) => apiRequest(appConfig.endpoints.teams, options),
};

export default api;
