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

// Specific API functions
export const api = {
  // Get welcome message
  getWelcomeMessage: () => apiRequest(appConfig.endpoints.home),

  // Get health status
  getHealthStatus: () => apiRequest(appConfig.endpoints.health),
};

export default api;
