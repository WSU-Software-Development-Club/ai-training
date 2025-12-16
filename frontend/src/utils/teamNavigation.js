/**
 * Team Navigation Utility
 *
 * Provides helper functions for navigating to team pages
 */

/**
 * Navigate to a team page
 *
 * @param {Function} navigate - React Router navigate function
 * @param {string} teamName - The team name to navigate to
 */
export const navigateToTeam = (navigate, teamName) => {
  if (!teamName) return;

  // Encode the team name for URL
  const encodedTeamName = encodeURIComponent(teamName);
  navigate(`/team/${encodedTeamName}`);
};

/**
 * Get the team page URL for a given team name
 *
 * @param {string} teamName - The team name
 * @returns {string} The team page URL
 */
export const getTeamPageUrl = (teamName) => {
  if (!teamName) return "#";
  const encodedTeamName = encodeURIComponent(teamName);
  return `/team/${encodedTeamName}`;
};

/**
 * Navigate to comparison page with two teams pre-selected
 *
 * @param {Function} navigate - React Router navigate function
 * @param {string} teamA - The first team name
 * @param {string} teamB - The second team name
 */
export const navigateToComparison = (navigate, teamA, teamB) => {
  if (!teamA || !teamB) return;

  // Encode team names for URL
  const encodedTeamA = encodeURIComponent(teamA);
  const encodedTeamB = encodeURIComponent(teamB);
  navigate(`/comparison?teamA=${encodedTeamA}&teamB=${encodedTeamB}`);
};
