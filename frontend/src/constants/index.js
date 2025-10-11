// Export all constants from a single file
export { colors } from "./colors";
export { spacing } from "./spacing";
export { breakpoints, mediaQueries } from "./breakpoints";
export { css } from "./css";

// App-specific constants
export const appConfig = {
  name: "NCAA Football",
  version: "1.0.0",
  apiUrl: process.env.REACT_APP_API_URL || "http://localhost:5000",
  endpoints: {
    home: "/",
    health: "/api/health",
    scores: "/api/scores",
    rankings: "/api/rankings/ap-top25",
    teams: "/api/teams",
    search: "/api/search",
    stats: "/api/stats",
    totalOffense: "/stats/offense",
  },
};
