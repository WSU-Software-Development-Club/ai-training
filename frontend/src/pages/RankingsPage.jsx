import React, { useState, useEffect } from "react";
import Header from "../components/Header";
import RankingsTable from "../components/RankingsTable";
import { appConfig } from "../constants";
import api from "../services/api";
import LoadingSpinner from "../components/LoadingSpinner";
import styles from "../styles/pages/RankingsPage.module.css";

const RankingsPage = () => {
  const [ranking, setRanking] = useState(null); // single ranking
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const handleSearch = (searchTerm) => {
    console.log("Searching for:", searchTerm);
  };
  useEffect(() => {
    const fetchRanking = async () => {
      try {
        const response = await api.getRankings(); // <-- use a named variable
        console.log("API response:", response.data); /* DEBUGGING PURPOSES */
        if (response.success) {
          setRanking(response.data);
        } else {
          setError("No rankings available");
        }
      } catch (err) {
        console.error(err);
        setError("Unable to load rankings.");
      } finally {
        setLoading(false);
      }
    };

    fetchRanking();
  }, []);

  return (
    <div className={styles.rankingsPage}>
      <Header title={appConfig.name} onSearch={handleSearch} />

      <main className={styles.rankingsPageMain}>
        <div className={styles.rankingsPageContainer}>
          <div className={styles.rankingsPageHeader}>
            <h1 className={styles.rankingsPageTitle}>AP Top 25 Rankings</h1>
            <p className={styles.rankingsPageSubtitle}>
              Current Associated Press College Football Rankings
            </p>
          </div>

          <div className={styles.rankingsPageContent}>
            {loading && <LoadingSpinner />}
            {error && <p className="error">{error}</p>}
            {ranking && (
              <RankingsTable rankings={ranking.data} title="AP Top 25" />
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default RankingsPage;
