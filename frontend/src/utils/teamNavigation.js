/**
 * Team Navigation Utility
 *
 * Provides helper functions for navigating to team pages
 */

import { findTeamByName } from "../matching/teamMatcher";

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
 * Resolve a "display" team name to a canonical team, then navigate.
 *
 * Some sources decorate the name with extra text the team API won't recognize,
 * e.g. AP rankings append first-place votes ("Indiana (66)") or use short
 * forms ("Southern Cal"). This strips trailing vote counts and runs the name
 * through the matcher (which understands abbreviations/alternate names) so the
 * team page loads for every team.
 *
 * @param {Function} navigate - React Router navigate function
 * @param {string} rawName - The possibly-decorated team name
 */
export const navigateToResolvedTeam = async (navigate, rawName) => {
  if (!rawName) return;

  // Drop a trailing "(<number>)" — AP rankings' first-place vote count — but
  // keep meaningful qualifiers like "(FL)"/"(OH)".
  const cleaned = rawName.replace(/\s*\(\d+\)\s*$/, "").trim();

  try {
    const team = await findTeamByName(cleaned);
    navigateToTeam(navigate, team?.school || cleaned);
  } catch {
    navigateToTeam(navigate, cleaned);
  }
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
