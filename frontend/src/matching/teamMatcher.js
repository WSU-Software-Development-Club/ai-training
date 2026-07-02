/**
 * Team Matcher Module
 *
 * PURPOSE: Find teams by name using various matching strategies
 *
 * This module handles the complex logic of matching team names, including:
 * - Building a lookup map for fast searching
 * - Trying multiple matching strategies (exact, fuzzy, partial)
 * - Handling different name formats and abbreviations
 *
 * WHY THIS EXISTS (for beginners):
 * - Team names are inconsistent across different data sources
 * - We need smart matching to handle "Washington St" vs "Washington State"
 * - Keeping matching logic separate makes it testable and maintainable
 */

import { getTeamData, getTeamDataSync } from "../data/teamDataService";
import {
  normalizeName,
  generateNameVariations,
  cleanNameForMatching,
  expandAbbreviations,
} from "./nameNormalizer";

// Lookup map for fast team name matching (built from team data)
let lookupMap = null;

/**
 * Build a lookup map that maps all possible team name variations to team objects
 *
 * This creates a Map where keys are normalized names and values are team objects.
 * We store multiple keys (variations) pointing to the same team.
 *
 * @param {Array} teamData - Array of team objects
 */
function buildLookupMap(teamData) {
  lookupMap = new Map();

  teamData.forEach((team) => {
    const normalizedSchool = normalizeName(team.school);
    const normalizedAbbrev = normalizeName(team.abbreviation);
    const normalizedAlternates = team.alternateNames.map((name) =>
      normalizeName(name)
    );
    const variations = generateNameVariations(normalizedSchool);

    // Collect all possible names for this team
    const allNames = [
      normalizedSchool,
      normalizedAbbrev,
      ...normalizedAlternates,
      ...variations,
    ].filter(Boolean); // Remove empty strings

    // Map each name variation to this team
    allNames.forEach((name) => {
      if (name && !lookupMap.has(name)) {
        lookupMap.set(name, team);
      }
    });
  });
}

/**
 * Initialize the lookup map (loads team data if needed)
 *
 * @returns {Promise<void>}
 */
async function initializeLookupMap() {
  if (lookupMap) {
    return; // Already initialized
  }

  const teamData = await getTeamData();
  buildLookupMap(teamData);
}

/**
 * Try to initialize the lookup map synchronously from already-cached data.
 *
 * @returns {boolean} true if the lookup map is ready, false otherwise
 */
function ensureLookupMapSync() {
  if (lookupMap) {
    return true;
  }

  const teamData = getTeamDataSync();
  if (!teamData) {
    return false; // Data not loaded yet — caller should use the async path
  }

  buildLookupMap(teamData);
  return true;
}

/**
 * Core matching logic. Assumes the lookup map is already built.
 *
 * @param {string} teamName - Team name to search for
 * @returns {Object|null} Team object or null if not found
 */
function matchTeam(teamName) {
  const normalized = normalizeName(teamName);

  // Strategy 1: Direct exact match
  if (lookupMap.has(normalized)) {
    return lookupMap.get(normalized);
  }

  // Strategy 2: Try with common suffixes removed
  const cleaned = cleanNameForMatching(normalized);
  if (cleaned && lookupMap.has(cleaned)) {
    return lookupMap.get(cleaned);
  }

  // Strategy 3: Try State/St variations
  const stateVariations = [
    normalized.replace(/\s+st\.?\s*$/i, " state"),
    normalized.replace(/\s+st\.?\s*$/i, " st"),
    normalized.replace(/\s+state\s*$/i, " st"),
  ];

  for (const variation of stateVariations) {
    if (variation && lookupMap.has(variation)) {
      return lookupMap.get(variation);
    }
  }

  // Strategy 4: Try expanding abbreviations
  const expanded = expandAbbreviations(normalized);
  if (expanded !== normalized && lookupMap.has(expanded)) {
    return lookupMap.get(expanded);
  }

  // Strategy 5: Partial substring matching (last resort)
  // Only use if both strings are reasonably long to avoid false matches
  if (normalized.length >= 5) {
    for (const [key, team] of lookupMap.entries()) {
      if (key.length >= 5) {
        // Check if one string contains the other
        if (key.includes(normalized) || normalized.includes(key)) {
          const minLength = Math.min(key.length, normalized.length);
          const matchLength = key.includes(normalized)
            ? normalized.length
            : key.length;

          // Require at least 70% of the shorter name to match
          if (matchLength >= minLength * 0.7) {
            return team;
          }
        }
      }
    }
  }

  // No match found
  return null;
}

/**
 * Synchronously find a team by name using already-cached data.
 *
 * Returns null if the team data hasn't been loaded into memory yet, in which
 * case callers should fall back to the async {@link findTeamByName}.
 *
 * @param {string} teamName - Team name to search for
 * @returns {Object|null} Team object, or null if not found / not loaded yet
 */
export function findTeamByNameSync(teamName) {
  if (!teamName) return null;
  if (!ensureLookupMapSync()) return null;
  return matchTeam(teamName);
}

/**
 * Find a team by name using exact and fuzzy matching strategies
 *
 * Tries multiple strategies in order:
 * 1. Direct exact match
 * 2. Match with common suffixes removed
 * 3. Match with State/St variations
 * 4. Match with abbreviations expanded
 * 5. Partial substring matching (as last resort)
 *
 * @param {string} teamName - Team name to search for
 * @returns {Promise<Object|null>} Team object or null if not found
 *
 * @example
 * const team = await findTeamByName("Washington St");
 * console.log(team.school); // "Washington State"
 */
export async function findTeamByName(teamName) {
  if (!teamName) return null;

  // Ensure lookup map is initialized
  await initializeLookupMap();

  return matchTeam(teamName);
}

/**
 * Test a team name match and return debug information
 *
 * Useful for debugging why a team name isn't matching
 *
 * @param {string} teamName - Team name to test
 * @returns {Promise<Object>} Debug information about the match
 *
 * @example
 * const debug = await testTeamMatch("Washington St");
 * console.log(debug);
 * // { input: "Washington St", normalized: "washington st",
 * //   found: true, team: {...} }
 */
export async function testTeamMatch(teamName) {
  await initializeLookupMap();

  const normalized = normalizeName(teamName);
  const match = await findTeamByName(teamName);

  return {
    input: teamName,
    normalized,
    found: !!match,
    team: match
      ? {
          school: match.school,
          abbreviation: match.abbreviation,
          hasLogo: !!match.logo,
          hasColor: !!match.primaryColor,
        }
      : null,
    inLookupMap: lookupMap?.has(normalized) || false,
  };
}
