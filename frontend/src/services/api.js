import { appConfig } from "../constants";

// Base API configuration
const API_BASE_URL = appConfig.apiUrl;

// Timeout utility - wraps fetch with a timeout
const fetchWithTimeout = (url, options = {}, timeout = 90000) => {
  return Promise.race([
    fetch(url, options),
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error("Request timeout")), timeout)
    ),
  ]);
};

// Retry utility with exponential backoff
const fetchWithRetry = async (
  url,
  options = {},
  retries = 3,
  timeout = 90000
) => {
  for (let i = 0; i < retries; i++) {
    try {
      const response = await fetchWithTimeout(url, options, timeout);
      return response;
    } catch (error) {
      const isLastRetry = i === retries - 1;
      if (isLastRetry) {
        throw error;
      }

      // Exponential backoff: wait 2^i seconds before retry
      const waitTime = Math.min(1000 * Math.pow(2, i), 10000);
      console.log(
        `Request failed, retrying in ${waitTime}ms... (attempt ${
          i + 1
        }/${retries})`
      );
      await new Promise((resolve) => setTimeout(resolve, waitTime));
    }
  }
};

// Generic API request function
const apiRequest = async (endpoint, options = {}) => {
  const url = `${API_BASE_URL}${endpoint}`;

  const defaultOptions = {
    headers: {
      "Content-Type": "application/json",
    },
  };

  const config = { ...defaultOptions, ...options };

  try {
    // Use 90 second timeout and 3 retries to handle Render spin-up
    const response = await fetchWithRetry(url, config, 3, 90000);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("API request failed:", error);
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

// Generic function to get stats for any category
export const getStats = async (category) => {
  const statId = STAT_NAME_TO_ID[category];
  if (!statId) {
    throw new Error(`No backend support for category: ${category}`);
  }
  return apiRequest(`/stats/stat/${statId}`);
};

// Specific API functions
export const api = {
  // Get welcome message
  getWelcomeMessage: () => apiRequest(appConfig.endpoints.home),

  // Get health status
  getHealthStatus: () => apiRequest(appConfig.endpoints.health),

  // Get stats for any supported category
  getStats,

  // Get AP rankings
  getRankings: () => apiRequest(appConfig.endpoints.rankings),

  // Get scoreboard by a given week
  getScoreboardByWeek: (week) => apiRequest(appConfig.endpoints.scores + week),

  // Get a given team's current season data
  getTeamData: (team) =>
    apiRequest(appConfig.endpoints.team + team + "/record"),

  // Get all teams
  getAllTeams: () => apiRequest(appConfig.endpoints.teams),
};

export default api;
