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
