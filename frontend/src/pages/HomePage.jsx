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

  // Fetch weekly game data on component mount
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
          <div className={styles.homePageContainer}>
            <div className={styles.homePageHeader}>
            <h1 className={styles.homePageTitle}>College Football Scores</h1>
            <p className={styles.homePageSubtitle}>
              Latest scores from across all conferences
            </p>
          </div>
            <div className={styles.loadingContainer}>
              <LoadingSpinner />
            </div>
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

  // Extract unique conferences, preserving original case for filtering
  const conferenceSet = new Set(
    gameData.games
      .flatMap((game) => [game.away.conference, game.home.conference])
      .filter(Boolean) // Remove null/undefined values
  );

  const conferences = [
    { value: "All", label: "All" },
    ...Array.from(conferenceSet)
      .sort()
      .map((conf) => ({
        value: conf,
        label: conf.charAt(0).toUpperCase() + conf.slice(1),
      })),
  ];

  const statuses = ["All", "Final", "Live", "Upcoming"];

  // Supports all possible weeks returned by getCurrentWeek (1–18)
  const weeks = Array.from({ length: 19 }, (_, i) => i + 1);

  // Filter scores based on selected filters
  const filteredScores = gameData.games.filter((game) => {
    const conferenceMatch =
      selectedConference === "All" ||
      (game.away.conference &&
        game.away.conference.toLowerCase() ===
          selectedConference.toLowerCase()) ||
      (game.home.conference &&
        game.home.conference.toLowerCase() ===
          selectedConference.toLowerCase());
    const statusMatch =
      selectedStatus === "All" ||
      (game.game_state.isUpcoming && selectedStatus === "Upcoming") ||
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
                  <option key={conference.value} value={conference.value}>
                    {conference.label}
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

          {/* Scores grouped by date to make it easier to scan */}
          <section className={styles.homePageSection}>
            {error && <p className="error">{error}</p>}

            {filteredScores.length === 0 && (
              <div className={styles.homePageNoResults}>
                <p>No scores found matching your filters.</p>
              </div>
            )}

            {filteredScores.length > 0 &&
              Object.entries(
                filteredScores.reduce((groups, game) => {
                  const { epoch } = game;

                  // Use the same base epoch field we use in ScoreCard for consistency
                  if (!epoch) {
                    const label = "TBD";
                    if (!groups[label]) {
                      groups[label] = {
                        sortKey: Number.MAX_SAFE_INTEGER,
                        games: [],
                      };
                    }
                    groups[label].games.push(game);
                    return groups;
                  }

                  const date = new Date(epoch * 1000);
                  const label = date.toLocaleDateString("en-US", {
                    weekday: "short",
                    month: "short",
                    day: "numeric",
                  });
                  const sortKey = date.setHours(0, 0, 0, 0);

                  if (!groups[label]) {
                    groups[label] = { sortKey, games: [] };
                  }

                  // Keep games collected under the same label
                  groups[label].games.push(game);

                  // Always store the earliest sortKey for that date label
                  if (sortKey < groups[label].sortKey) {
                    groups[label].sortKey = sortKey;
                  }

                  return groups;
                }, {})
              )
                .sort(([, aData], [, bData]) => aData.sortKey - bData.sortKey)
                .map(([dateLabel, { games }]) => (
                  <div key={dateLabel} className={styles.homePageDateGroup}>
                    <h2 className={styles.homePageDateHeading}>{dateLabel}</h2>
                    <div className={styles.homePageScoresGrid}>
                      {games.map((game) => (
                        <ScoreCard
                          key={`${game.home?.names?.char6}-${game.away?.names?.char6}-${game.epoch}`}
                          game={game}
                        />
                      ))}
                    </div>
                  </div>
                ))}
          </section>
        </div>
      </main>
    </div>
  );
};

export default HomePage;
