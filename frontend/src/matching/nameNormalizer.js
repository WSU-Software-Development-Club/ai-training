/**
 * Name Normalizer Module
 * 
 * PURPOSE: Provides functions to normalize team names for consistent matching
 * 
 * This module contains PURE FUNCTIONS - they don't modify anything outside
 * themselves, they just take input and return output. This makes them:
 * - Easy to understand
 * - Easy to test
 * - Easy to reuse
 * 
 * WHY THIS EXISTS (for beginners):
 * - Team names come in many formats: "Florida St.", "Florida State", "FSU"
 * - We need to convert all variations to a standard format for matching
 * - Keeping normalization separate makes the code easier to maintain
 */

/**
 * Normalize a team name to lowercase, remove punctuation and extra whitespace
 * 
 * @param {string} name - Team name to normalize
 * @returns {string} Normalized name
 * 
 * @example
 * normalizeName("Florida St.") // returns "florida st"
 * normalizeName("Miami (FL)") // returns "miami fl"
 * normalizeName("Miami (OH)") // returns "miami oh"
 */
export function normalizeName(name) {
  if (!name) return '';

  return name
    .trim()
    .toLowerCase()
    // Convert parentheses and periods to spaces. We must NOT drop the
    // parenthetical content: the state qualifier is what distinguishes
    // "Miami (FL)" (Hurricanes) from "Miami (OH)" (RedHawks). Removing it made
    // both collapse to "miami" and share one logo.
    .replace(/[().]/g, ' ')
    .replace(/\s+/g, ' ') // Normalize whitespace to single spaces
    .trim(); // Trim again after removals
}

/**
 * Generate common variations of a team name
 * 
 * For example, "Florida State" can be written as "Florida St", "Florida St.", etc.
 * This function generates these variations to improve matching.
 * 
 * @param {string} normalizedName - Already normalized team name
 * @returns {Array<string>} Array of name variations
 * 
 * @example
 * generateNameVariations("florida state")
 * // returns ["florida st", "florida st."]
 */
export function generateNameVariations(normalizedName) {
  const variations = [];
  
  // State variations
  if (normalizedName.includes(' state')) {
    variations.push(normalizedName.replace(' state', ' st'));
    variations.push(normalizedName.replace(' state', ' st.'));
  }
  if (normalizedName.includes(' st')) {
    variations.push(normalizedName.replace(' st', ' state'));
  }
  
  // Florida variations
  if (normalizedName.includes('florida')) {
    variations.push(normalizedName.replace('florida', 'fla'));
    variations.push(normalizedName.replace('florida', 'fl'));
  }
  
  // North Carolina variations
  if (normalizedName.includes('north carolina')) {
    variations.push(normalizedName.replace('north carolina', 'nc'));
    variations.push(normalizedName.replace('north carolina', 'n carolina'));
  }
  
  // South Carolina variations
  if (normalizedName.includes('south carolina')) {
    variations.push(normalizedName.replace('south carolina', 'sc'));
    variations.push(normalizedName.replace('south carolina', 's carolina'));
  }
  
  return variations;
}

/**
 * Clean a normalized name by removing common suffixes
 * 
 * This helps with fuzzy matching by removing words like "State", "University", etc.
 * 
 * @param {string} normalizedName - Already normalized team name
 * @returns {string} Cleaned name
 * 
 * @example
 * cleanNameForMatching("washington state university")
 * // returns "washington"
 */
export function cleanNameForMatching(normalizedName) {
  return normalizedName
    .replace(/\s+(st|state|university|college)$/i, '')
    .replace(/^the\s+/i, '')
    .replace(/\s+st\s*$/i, '')
    .replace(/\s+state\s*$/i, '')
    .trim();
}

/**
 * Map of common abbreviations to full names
 * Used for expanding abbreviated team names
 */
export const abbreviationMap = {
  'fla': 'florida',
  'fl': 'florida',
  'nc': 'north carolina',
  'n carolina': 'north carolina',
  'sc': 'south carolina',
  's carolina': 'south carolina',
};

/**
 * Expand abbreviations in a team name
 * 
 * @param {string} normalizedName - Already normalized team name
 * @returns {string} Name with abbreviations expanded
 * 
 * @example
 * expandAbbreviations("fla state") // returns "florida state"
 */
export function expandAbbreviations(normalizedName) {
  let expanded = normalizedName;
  
  for (const [abbrev, full] of Object.entries(abbreviationMap)) {
    const regex = new RegExp(`\\b${abbrev}\\b`, 'gi');
    expanded = expanded.replace(regex, full);
  }
  
  return expanded;
}

