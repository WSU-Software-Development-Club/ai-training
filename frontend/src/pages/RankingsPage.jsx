import React, { useState, useEffect } from "react";
import RankingsTable from "../components/RankingsTable";
import api from "../services/api";
import LoadingSpinner from "../components/LoadingSpinner";
import styles from "../styles/pages/RankingsPage.module.css";

const RankingsPage = () => {
  const [ranking, setRanking] = useState(null); // single ranking
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const controller = new AbortController();

    const fetchRanking = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await api.getRankings({ signal: controller.signal });
        if (response.success) {
          setRanking(response.data);
        } else {
          setError("No rankings available.");
        }
      } catch (err) {
        // Request was cancelled because the user navigated away — not an error.
        if (err.name === "AbortError") return;
        console.error(err);
        setError("Unable to load rankings.");
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    };

    fetchRanking();

    return () => controller.abort();
  }, []);

  return (
    <div className={styles.rankingsPage}>
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
