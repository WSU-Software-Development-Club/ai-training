/**
 * Team Branding API Module
 *
 * PURPOSE: Main public API for getting team branding information
 *
 * This is the ONLY file that other parts of the app should import from.
 * It orchestrates the data loading and matching logic but doesn't implement
 * any of that logic itself - it just delegates to the right modules.
 *
 * WHY THIS EXISTS (for beginners):
 * - Provides a simple, clean interface for getting team logos and colors
 * - Hides the complexity of data loading and name matching
 * - Makes it easy to change internal implementation without breaking the app
 *
 * HOW TO USE:
 * ```javascript
 * import { getTeamBranding } from '../branding/teamBranding';
 *
 * const branding = await getTeamBranding("Alabama");
 * console.log(branding.logo); // URL to Alabama's logo
 * console.log(branding.primaryColor); // Alabama's primary color
 * ```
 */

import { findTeamByName, testTeamMatch } from "../matching/teamMatcher";
import { preloadTeamData as preloadData } from "../data/teamDataService";

/**
 * Get team branding information by team name
 *
 * Returns an object with logo URLs, colors, and other branding info.
 * Returns null if the team is not found.
 *
 * @param {string} teamName - Name of the team (e.g., "Alabama", "Ohio State")
 * @returns {Promise<Object|null>} Branding information or null
 *
 * @example
 * const branding = await getTeamBranding("Florida State");
 * if (branding) {
 *   console.log(branding.logo);          // Logo URL
 *   console.log(branding.primaryColor);  // Hex color code
 *   console.log(branding.conference);    // "ACC"
 * }
 */
export async function getTeamBranding(teamName) {
  if (!teamName) return null;

  // Use the matcher to find the team
  const team = await findTeamByName(teamName);

  if (!team) {
    return null;
  }

  // Return only the branding-related information
  return {
    logo: team.logo,
    logoDark: team.logoDark,
    primaryColor: team.primaryColor,
    alternateColor: team.alternateColor,
    conference: team.conference,
    school: team.school,
    abbreviation: team.abbreviation,
  };
}

/**
 * Preload team data when the app starts
 *
 * Call this function early in your app (e.g., in App.jsx) to load
 * team data in the background. This prevents delays later when users
 * need branding information.
 *
 * @returns {Promise<void>}
 *
 * @example
 * // In App.jsx:
 * import { preloadTeamData } from './branding/teamBranding';
 *
 * function App() {
 *   useEffect(() => {
 *     preloadTeamData();
 *   }, []);
 *   // ...
 * }
 */
export async function preloadTeamData() {
  await preloadData();
}

/**
 * Test if a team name can be found (for debugging)
 *
 * @param {string} teamName - Team name to test
 * @returns {Promise<Object>} Debug information
 *
 * @example
 * const result = await testTeamMatching("Wash St");
 * console.log(result.found);  // true or false
 * console.log(result.team);   // matched team info
 */
export async function testTeamMatching(teamName) {
  return await testTeamMatch(teamName);
}
