/**
 * Team Data Service Module
 *
 * PURPOSE: Manages team data cache and provides access to team information
 *
 * This module handles:
 * - Caching team data so we don't reload the CSV multiple times
 * - Transforming raw CSV data into a format our app can use
 * - Providing functions to access the cached data
 *
 * WHY THIS EXISTS (for beginners):
 * - Loading CSV files is slow, so we cache the result
 * - Separates data management from business logic
 * - Makes it easy to test and debug data-related issues
 */

import { loadCSV } from "./csvLoader";

// In-memory cache for team data (null = not loaded yet)
let teamDataCache = null;

/**
 * Transform raw CSV row into app-friendly team object
 *
 * @param {Object} csvRow - Raw CSV row object
 * @returns {Object} Transformed team object
 */
function transformTeamData(csvRow) {
  // Parse logo URLs (comma-separated in CSV)
  const logos = csvRow.Logos
    ? csvRow.Logos.split(",").map((url) => url.trim())
    : [];

  return {
    id: csvRow.Id,
    school: csvRow.School,
    abbreviation: csvRow.Abbreviation,
    conference: csvRow.Conference,
    primaryColor: csvRow.Color || null,
    alternateColor: csvRow.AlternateColor || null,
    logo: logos[0] || null,
    logoDark: logos[1] || logos[0] || null,
    // Store alternate names as array (comma-separated in CSV)
    alternateNames: csvRow.AlternateNames
      ? csvRow.AlternateNames.split(",").map((name) => name.trim())
      : [],
  };
}

/**
 * Load team data from CSV and cache it
 *
 * @returns {Promise<Array>} Array of team objects
 */
async function loadAndCacheTeamData() {
  if (teamDataCache) {
    return teamDataCache;
  }

  try {
    const rawData = await loadCSV("cfb_teams.csv");
    teamDataCache = rawData.map(transformTeamData);
    return teamDataCache;
  } catch (error) {
    console.error("Failed to load team data:", error);
    return [];
  }
}

/**
 * Get all team data (loads from cache if available)
 *
 * @returns {Promise<Array>} Array of team objects
 *
 * @example
 * const teams = await getTeamData();
 * console.log(teams[0].school); // "Alabama"
 */
export async function getTeamData() {
  return await loadAndCacheTeamData();
}

/**
 * Preload team data (call this when app starts to avoid delays later)
 *
 * @returns {Promise<void>}
 *
 * @example
 * // In App.jsx or index.js:
 * preloadTeamData();
 */
export async function preloadTeamData() {
  await loadAndCacheTeamData();
}

/**
 * Clear the cache (useful for testing or if data needs to be reloaded)
 */
export function clearCache() {
  teamDataCache = null;
}
