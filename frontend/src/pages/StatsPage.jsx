import React, { useState, useEffect } from "react";
import Header from "../components/Header";
import StatsTable from "../components/StatsTable";
import { appConfig } from "../constants";
import { mockStats, statCategories } from "../utils/mockData";
import { getStats, hasBackendSupport } from "../services/api";
import LoadingSpinner from "../components/LoadingSpinner";
import styles from "../styles/pages/StatsPage.module.css";

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
    <div className={styles.statsPage}>
      <Header title={appConfig.name} onSearch={handleSearch} />

      <main className={styles.statsPageMain}>
        <div className={styles.statsPageContainer}>
          <div className={styles.statsPageHeader}>
            <h1 className={styles.statsPageTitle}>Team Statistics</h1>
            <p className={styles.statsPageSubtitle}>
              View team statistics across different categories
            </p>
          </div>

          <div className={styles.statsPageFilters}>
            <div className={styles.statsPageFilterGroup}>
              <label className={styles.statsPageFilterLabel}>
                Stat Category:
              </label>
              <select
                className={styles.statsPageFilterSelect}
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

          <div className={styles.statsPageContent}>
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
