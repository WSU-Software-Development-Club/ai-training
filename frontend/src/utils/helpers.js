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

export const getCurrentWeek = () => {
  
  const startDate = new Date();
  startDate.setMonth(7);
  startDate.setDate(23);

  const endDate = new Date();
  endDate.setMonth(11);
  endDate.setDate(13);

  const currentDate = new Date();

  if (currentDate.getMonth() < 7)
    return 1;
  if (currentDate.getMonth() > 11)
    return 16;
  
  const daysSinceStart = Math.floor(
    (currentDate - startDate) / (1000 * 60 * 60 * 24)
  )

  const weeks = Math.floor(
    (daysSinceStart / 7) + 1
  )

  return weeks;
}