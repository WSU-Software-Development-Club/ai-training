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

// Default season week for the scoreboard/predictions views. A CFB season is
// named for the year it starts (late August) and runs into January.
//   - January: the prior year's season is still in its postseason (bowls /
//     playoff) → week 19.
//   - Feb–Jul: offseason before the upcoming season → default to opening week 1
//     (the new schedule is already published, so we point at it, not last year).
//   - Aug–Dec: in season → count weeks from the ~Aug 23 opener so it advances
//     week-by-week as games happen.
export const getCurrentWeek = () => {
  const now = new Date();
  const month = now.getMonth(); // 0 = Jan … 11 = Dec

  if (month === 0) return 19; // January postseason of the prior season
  if (month <= 6) return 1; // Feb–Jul: upcoming season, opening week

  const start = new Date(now.getFullYear(), 7, 23); // Aug 23 opener
  const daysSinceStart = Math.floor((now - start) / (1000 * 60 * 60 * 24));
  const week = Math.floor(daysSinceStart / 7) + 1;
  return Math.min(19, Math.max(1, week));
};

// Default season year, paired with getCurrentWeek above. In January we're still
// in the prior year's season (its bowls/playoff), so that season's year applies;
// from February on (offseason through the in-progress season) the current
// calendar year's season is the one to show.
export const getCurrentYear = () => {
  const now = new Date();
  if (now.getMonth() === 0) return now.getFullYear() - 1;
  return now.getFullYear();
};