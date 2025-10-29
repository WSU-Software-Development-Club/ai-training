import React, { useState, useEffect } from "react";
import Header from "../components/Header";
import StatsTable from "../components/StatsTable";
import { appConfig } from "../constants";
import { mockStats, statCategories } from "../utils/mockData";
import { getStats, hasBackendSupport } from "../services/api";
import LoadingSpinner from "../components/LoadingSpinner"
import "../styles/pages/StatsPage.css";

const StatsPage = () => {
  const [selectedCategory, setSelectedCategory] = useState("Total Offense");
  const [stats, setStats] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSearch = (searchTerm) => {
    // TODO: Replace with API call to /api/search
    console.log("Searching for:", searchTerm);
  };

  // Fetch stats data when category changes
  useEffect(() => {
    const fetchStats = async () => {
      // Check if this category has backend support
      if (hasBackendSupport(selectedCategory)) {
        setLoading(true);
        setError(null);
        try {
          const response = await getStats(selectedCategory);
          if (response.success && response.data && response.data.data) {
            setStats(response.data.data);
          } else {
            setError(`Failed to fetch ${selectedCategory} statistics`);
            setStats([]);
          }
        } catch (err) {
          console.error(`Error fetching ${selectedCategory} stats:`, err);
          setError(`Error loading ${selectedCategory} statistics`);
          setStats([]);
        } finally {
          setLoading(false);
        }
      } else {
        // Use mock data for categories without backend support
        setStats(mockStats[selectedCategory] || []);
        setError(null);
        setLoading(false);
      }
    };

    fetchStats();
  }, [selectedCategory]);

  const currentStats = stats;

  return (
    <div className="stats-page">
      <Header title={appConfig.name} onSearch={handleSearch} />

      <main className="stats-page__main">
        <div className="stats-page__container">
          <div className="stats-page__header">
            <h1 className="stats-page__title">Team Statistics</h1>
            <p className="stats-page__subtitle">
              View team statistics across different categories
            </p>
          </div>

          <div className="stats-page__filters">
            <div className="stats-page__filter-group">
              <label className="stats-page__filter-label">Stat Category:</label>
              <select
                className="stats-page__filter-select"
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
              >
                {statCategories.map((category) => (
                  <option key={category} value={category}>
                    {category}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="stats-page__content">
            {loading && <LoadingSpinner />}

            {error && <div className="stats-page__error">{error}</div>}

            {!loading && !error && (
              <StatsTable
                stats={currentStats}
                title={selectedCategory}
                statCategory={selectedCategory}
              />
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default StatsPage;
