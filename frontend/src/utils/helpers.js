// Utility helper functions

// Format text with proper capitalization
export const capitalize = (str) => {
  if (!str) return "";
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
};

// Format status text
export const formatStatus = (status) => {
  return capitalize(status);
};

// Proper display names for NCAA conference slugs (the API returns SEO-style
// values like "big-ten" / "cusa" / "sec"). Anything not listed falls back to
// a title-cased version of the slug.
const CONFERENCE_DISPLAY_NAMES = {
  acc: "ACC",
  american: "American",
  "big-12": "Big 12",
  "big-ten": "Big Ten",
  cusa: "C-USA",
  sec: "SEC",
  "sun-belt": "Sun Belt",
  "pac-12": "Pac-12",
  "mountain-west": "Mountain West",
  "mid-american": "MAC",
  "fbs-independents": "FBS Independents",
  independent: "Independent",
};

// Convert a conference slug/name into a human-friendly display label.
export const formatConferenceName = (conference) => {
  if (!conference) return "";

  const key = conference.trim().toLowerCase();
  if (CONFERENCE_DISPLAY_NAMES[key]) {
    return CONFERENCE_DISPLAY_NAMES[key];
  }

  // Fallback: title-case each hyphen/space separated word.
  return key
    .split(/[-\s]+/)
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
};

// Check if a value is empty or null
export const isEmpty = (value) => {
  return value === null || value === undefined || value === "";
};

// Generate a random ID (useful for keys)
export const generateId = () => {
  return Math.random().toString(36).substr(2, 9);
};

// Debounce function for performance optimization
export const debounce = (func, wait) => {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
};

// Get current week
export const getCurrentWeek = () => {
  const startDate = new Date();
  startDate.setMonth(7);
  startDate.setDate(23);

  const currentDate = new Date();

  if (currentDate.getMonth() < 7)
  {
    return 19;
  }

  const daysSinceStart = Math.floor(
    (currentDate - startDate) / (1000 * 60 * 60 * 24)
  );

  const weeks = Math.floor(daysSinceStart / 7 + 1);

  return weeks > 19 ? 19 : weeks;
};

export const getCurrentYear = () => {
  const currentDate = new Date();
  if (currentDate.getMonth() < 7) {
    return currentDate.getFullYear() - 1;
  }
  return currentDate.getFullYear();
}