/**
 * CSV Loader Module
 *
 * PURPOSE: Loads and parses CSV files from the public folder
 *
 * This module is responsible for ONLY loading CSV data. It doesn't know
 * what the data means or how it will be used - it just fetches and parses.
 *
 * WHY THIS EXISTS (for beginners):
 * - Separates file loading from business logic
 * - Uses PapaParse library for reliable CSV parsing
 * - Makes it easy to swap data sources later if needed
 */

import Papa from "papaparse";

/**
 * Load and parse a CSV file from the public folder
 *
 * @param {string} filename - Name of the CSV file (e.g., 'cfb_teams.csv')
 * @returns {Promise<Array>} Array of objects where keys are column headers
 *
 * @example
 * const teams = await loadCSV('cfb_teams.csv');
 * // Returns: [{ Id: '1', School: 'Alabama', ... }, ...]
 */
export async function loadCSV(filename) {
  try {
    const response = await fetch(`${process.env.PUBLIC_URL || ""}/${filename}`);

    if (!response.ok) {
      throw new Error(`Failed to load ${filename}: ${response.statusText}`);
    }

    const csvText = await response.text();

    // Use PapaParse to convert CSV text into array of objects
    return new Promise((resolve, reject) => {
      Papa.parse(csvText, {
        header: true, // First row is column names
        skipEmptyLines: true, // Ignore empty rows
        trimHeaders: true, // Remove whitespace from headers
        complete: (results) => {
          if (results.errors.length > 0) {
            console.warn("CSV parsing warnings:", results.errors);
          }
          resolve(results.data);
        },
        error: (error) => {
          reject(new Error(`CSV parsing error: ${error.message}`));
        },
      });
    });
  } catch (error) {
    console.error("Error loading CSV:", error);
    throw error;
  }
}
