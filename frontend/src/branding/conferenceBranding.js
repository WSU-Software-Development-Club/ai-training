/**
 * Conference Branding Utility
 *
 * Provides conference colors and branding information for FBS conferences.
 * Since the CSV doesn't include conference logos/colors, these are manually defined.
 */

/**
 * Conference branding data
 * Colors are based on common conference branding
 */
const conferenceBranding = {
  ACC: {
    name: "ACC",
    displayName: "Atlantic Coast Conference",
    primaryColor: "#013ca6",
    secondaryColor: "#ff6600",
    logo: null, // Can be added later if conference logos are sourced
  },
  "Big Ten": {
    name: "Big Ten",
    displayName: "Big Ten Conference",
    primaryColor: "#1e3a8a",
    secondaryColor: "#fbbf24",
    logo: null,
  },
  "Big 12": {
    name: "Big 12",
    displayName: "Big 12 Conference",
    primaryColor: "#000000",
    secondaryColor: "#ff0000",
    logo: null,
  },
  SEC: {
    name: "SEC",
    displayName: "Southeastern Conference",
    primaryColor: "#0d2240",
    secondaryColor: "#ffd700",
    logo: null,
  },
  "Pac-12": {
    name: "Pac-12",
    displayName: "Pac-12 Conference",
    primaryColor: "#004b91",
    secondaryColor: "#c60c30",
    logo: null,
  },
  "Mountain West": {
    name: "Mountain West",
    displayName: "Mountain West Conference",
    primaryColor: "#003366",
    secondaryColor: "#ffcc00",
    logo: null,
  },
  "American Athletic": {
    name: "American Athletic",
    displayName: "American Athletic Conference",
    primaryColor: "#0c2340",
    secondaryColor: "#c8102e",
    logo: null,
  },
  "Sun Belt": {
    name: "Sun Belt",
    displayName: "Sun Belt Conference",
    primaryColor: "#8b0000",
    secondaryColor: "#ffd700",
    logo: null,
  },
  "Mid-American": {
    name: "Mid-American",
    displayName: "Mid-American Conference",
    primaryColor: "#003366",
    secondaryColor: "#ff6600",
    logo: null,
  },
  "Conference USA": {
    name: "Conference USA",
    displayName: "Conference USA",
    primaryColor: "#003087",
    secondaryColor: "#c8102e",
    logo: null,
  },
  "FBS Independents": {
    name: "FBS Independents",
    displayName: "FBS Independents",
    primaryColor: "#666666",
    secondaryColor: "#cccccc",
    logo: null,
  },
};

/**
 * Normalize conference name for lookup
 */
function normalizeConferenceName(name) {
  if (!name) return "";
  return name.trim();
}

/**
 * Get conference branding by conference name
 * @param {string} conferenceName - The conference name to look up
 * @returns {Object|null} Conference branding data or null if not found
 */
export function getConferenceBranding(conferenceName) {
  if (!conferenceName) return null;

  const normalized = normalizeConferenceName(conferenceName);

  // Direct lookup
  if (conferenceBranding[normalized]) {
    return conferenceBranding[normalized];
  }

  // Try case-insensitive lookup
  const lower = normalized.toLowerCase();
  for (const [key, value] of Object.entries(conferenceBranding)) {
    if (
      key.toLowerCase() === lower ||
      value.displayName.toLowerCase() === lower
    ) {
      return value;
    }
  }

  // Return default/unknown conference branding
  return {
    name: normalized,
    displayName: normalized,
    primaryColor: "#666666",
    secondaryColor: "#999999",
    logo: null,
  };
}

/**
 * Get all conference branding data
 */
export function getAllConferenceBranding() {
  return conferenceBranding;
}

