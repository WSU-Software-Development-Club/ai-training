import React, { useState, useEffect } from "react";
import Header from "../components/Header";
import ScoreCard from "../components/ScoreCard";
import { appConfig } from "../constants";
import api from "../services/api";
import styles from "../styles/pages/HomePage.module.css";
import { getCurrentWeek } from "../utils/helpers";
import LoadingSpinner from "../components/LoadingSpinner";

const HomePage = () => {
  const [selectedConference, setSelectedConference] = useState("All");
  const [selectedStatus, setSelectedStatus] = useState("All");
  const [selectedWeek, setSelectedWeek] = useState(getCurrentWeek());
  const [gameData, setGameData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const handleSearch = (searchTerm) => {
    // TODO: Replace with API call to /api/search
    console.log("Searching for:", searchTerm);
  };

  useEffect(() => {
    const fetchGameData = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await api.getScoreboardByWeek(selectedWeek);

        if (response.success) {
          setGameData(response.data);
        } else {
          setError("No scoreboard data available.");
        }
      } catch (err) {
        console.error(err);
        setError("Unable to load scoreboard data.");
      } finally {
        setLoading(false);
      }
    };

    fetchGameData();
  }, [selectedWeek]);

  if (loading) {
    return (
      <div className={styles.homePage}>
        <Header title={appConfig.name} onSearch={handleSearch} />
        <main className={styles.homePageMain}>
          <div className={styles.loadingContainer}>
            <LoadingSpinner />
          </div>
        </main>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.homePage}>
        <Header title={appConfig.name} onSearch={handleSearch} />
        <main className={styles.homePageMain}>
          <div className={styles.errorContainer}>
            <p>{error}</p>
          </div>
        </main>
      </div>
    );
  }

  const conferences = [
    "All",
    ...new Set(gameData.games.flatMap((game) => [
      game.away.conference.charAt(0).toUpperCase() + game.away.conference.slice(1),
      game.home.conference.charAt(0).toUpperCase() + game.home.conference.slice(1),
  ])),
  ];

  const statuses = ["All", "Final", "Live", "Upcoming"];

  const weeks = Array.from({ length: 14}, (_, i) => i + 1);

  // Filter scores based on selected filters
  const filteredScores = gameData.games.filter(game => {
    const conferenceMatch =
      selectedConference === "All" || game.away.conference === selectedConference || game.home.conference === selectedConference;
    const statusMatch =
      selectedStatus === "All" || (game.game_state.isUpcoming && selectedStatus === "Upcoming") ||
      (game.game_state.isLive && selectedStatus === "Live") || 
      (game.game_state.isFinished && selectedStatus === "Final");
    return conferenceMatch && statusMatch;
  });

  return (
    <div className={styles.homePage}>
      <Header title={appConfig.name} onSearch={handleSearch} />

      <main className={styles.homePageMain}>
        <div className={styles.homePageContainer}>
          <div className={styles.homePageHeader}>
            <h1 className={styles.homePageTitle}>College Football Scores</h1>
            <p className={styles.homePageSubtitle}>
              Latest scores from across all conferences
            </p>
          </div>

          <div className={styles.homePageFilters}>
            {/* Week Dropdown */}
            <div className={styles.homePageFilterGroup}>
              <label className={styles.homePageFilterLabel}>Week:</label>
              <select
                className={styles.homePageFilterSelect}
                value={selectedWeek}
                onChange={(e) => setSelectedWeek(Number(e.target.value))}
              >
                {weeks.map((weekNumber) => (
                  <option key={weekNumber} value={weekNumber}>
                    Week {weekNumber}
                  </option>
                ))}
              </select>
            </div>
            <div className={styles.homePageFilterGroup}>
              <label className={styles.homePageFilterLabel}>Conference:</label>
              <select
                className={styles.homePageFilterSelect}
                value={selectedConference}
                onChange={(e) => setSelectedConference(e.target.value)}
              >
                {conferences.map((conference) => (
                  <option key={conference} value={conference}>
                    {conference}
                  </option>
                ))}
              </select>
            </div>

            <div className={styles.homePageFilterGroup}>
              <label className={styles.homePageFilterLabel}>Status:</label>
              <select
                className={styles.homePageFilterSelect}
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
              >
                {statuses.map((status) => (
                  <option key={status} value={status}>
                    {status}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Recent Scores Section */}
          <section className={styles.homePageSection}>
            <div className={styles.homePageScoresGrid}>
              {error && <p className="error">{error}</p>}
              {filteredScores.slice(0, 6).map((game) => (
                <ScoreCard 
                key={`${game.home?.names?.char6}-${game.away?.names?.char6}`}
                game={game} 
                />
              ))}
            </div>

            {filteredScores.length === 0 && (
              <div className={styles.homePageNoResults}>
                <p>No scores found matching your filters.</p>
              </div>
            )}

          </section>
        </div>
      </main>
    </div>
  );
};

export default HomePage;
