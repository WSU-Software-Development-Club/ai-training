import { appConfig } from "../constants";

// Base API configuration
const API_BASE_URL = appConfig.apiUrl;

// Generic API request function
const apiRequest = async (endpoint, options = {}) => {
  const url = `${API_BASE_URL}${endpoint}`;

  const defaultOptions = {
    headers: {
      "Content-Type": "application/json",
    },
  };

  const config = { ...defaultOptions, ...options };

  try {
    const response = await fetch(url, config);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("API request failed:", error);
    throw error;
  }
};

// Category to endpoint mapping
const STAT_CATEGORY_ENDPOINTS = {
  "Total Offense": "/stats/offense",
  "Total Defense": "/stats/defense",
  "Rushing Offense": "/stats/offense/rushing",
  "Rushing Defense": "/stats/defense/rushing",
  // Add more categories as backend endpoints become available
};

// Check if a category has backend support
export const hasBackendSupport = (category) => {
  return STAT_CATEGORY_ENDPOINTS.hasOwnProperty(category);
};

// Generic function to get stats for any category
export const getStats = async (category) => {
  const endpoint = STAT_CATEGORY_ENDPOINTS[category];
  if (!endpoint) {
    throw new Error(`No backend support for category: ${category}`);
  }
  return apiRequest(endpoint);
};

// Specific API functions
export const api = {
  // Get welcome message
  getWelcomeMessage: () => apiRequest(appConfig.endpoints.home),

  // Get health status
  getHealthStatus: () => apiRequest(appConfig.endpoints.health),

  // Get stats for any supported category
  getStats,
};

export default api;
