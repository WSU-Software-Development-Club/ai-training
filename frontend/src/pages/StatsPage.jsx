import React, { useState, useEffect } from "react";
import StatsTable from "../components/StatsTable";
import { mockStats } from "../utils/mockData";
import { statCategories } from "../utils/appData";
import { getStats, hasBackendSupport, peekStats } from "../services/api";
import LoadingSpinner from "../components/LoadingSpinner";
import styles from "../styles/pages/StatsPage.module.css";

const StatsPage = () => {
  const [selectedCategory, setSelectedCategory] = useState("Total Offense");
  const [stats, setStats] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch stats data when category changes
  useEffect(() => {
    const controller = new AbortController();

    // Instant path: if this category was already prefetched into the cache,
    // render it synchronously — no async gap, no loading flash.
    if (hasBackendSupport(selectedCategory)) {
      const cached = peekStats(selectedCategory);
      if (cached) {
        if (cached.success && cached.data && cached.data.data) {
          setStats(cached.data.data);
          setError(null);
        } else {
          setError(`Failed to fetch ${selectedCategory} statistics`);
          setStats([]);
        }
        setLoading(false);
        return () => controller.abort();
      }
    }

    const fetchStats = async () => {
      // Check if this category has backend support
      if (hasBackendSupport(selectedCategory)) {
        setLoading(true);
        setError(null);
        try {
          const response = await getStats(selectedCategory, {
            signal: controller.signal,
          });
          if (response.success && response.data && response.data.data) {
            setStats(response.data.data);
          } else {
            setError(`Failed to fetch ${selectedCategory} statistics`);
            setStats([]);
          }
        } catch (err) {
          // Cancelled because the user navigated away — not an error.
          if (err.name === "AbortError") return;
          console.error(`Error fetching ${selectedCategory} stats:`, err);
          setError(`Error loading ${selectedCategory} statistics`);
          setStats([]);
        } finally {
          if (!controller.signal.aborted) {
            setLoading(false);
          }
        }
      } else {
        // Use mock data for categories without backend support
        setStats(mockStats[selectedCategory] || []);
        setError(null);
        setLoading(false);
      }
    };

    fetchStats();

    return () => controller.abort();
  }, [selectedCategory]);

  const currentStats = stats;

  return (
    <div className={styles.statsPage}>
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
