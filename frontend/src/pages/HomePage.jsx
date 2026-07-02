import React, { useState, useEffect } from "react";
import Header from "../components/Header";
import ScoreCard from "../components/ScoreCard";
import { appConfig } from "../constants";
import api from "../services/api";
import styles from "../styles/pages/HomePage.module.css";
import { getCurrentWeek } from "../utils/helpers";
import { getCurrentYear } from "../utils/helpers";
import { formatConferenceName } from "../utils/helpers";
import LoadingSpinner from "../components/LoadingSpinner";

const HomePage = () => {
  const [selectedConference, setSelectedConference] = useState("All");
  const [selectedStatus, setSelectedStatus] = useState("All");
  const [selectedWeek, setSelectedWeek] = useState(getCurrentWeek());
  const [selectedYear, setSelectedYear] = useState(getCurrentYear());
  const [selectedDate, setSelectedDate] = useState("All");
  const [gameData, setGameData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const handleSearch = (searchTerm) => {
    // TODO: Replace with API call to /api/search
    console.log("Searching for:", searchTerm);
  };

  // Reset date filter when week or year changes
  useEffect(() => {
    setSelectedDate("All");
  }, [selectedWeek, selectedYear]);

  // Fetch weekly game data when the selected week/year changes.
  useEffect(() => {
    const controller = new AbortController();

    // Instant path: if this week was already prefetched into the cache, render
    // it synchronously — no async gap, no loading flash.
    const cached = api.peekScoreboardByWeek(selectedWeek, selectedYear);
    if (cached) {
      if (cached.success) {
        setGameData(cached.data);
        setError(null);
      } else {
        setError("No scoreboard data available.");
      }
      setLoading(false);
      return () => controller.abort();
    }

    const fetchGameData = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await api.getScoreboardByWeek(
          selectedWeek,
          selectedYear,
          { signal: controller.signal }
        );

        if (response.success) {
          setGameData(response.data);
        } else {
          setError("No scoreboard data available.");
        }
      } catch (err) {
        // Request was cancelled because the user navigated away — not an error.
        if (err.name === "AbortError") return;
        console.error(err);
        setError("Unable to load scoreboard data.");
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    };

    fetchGameData();

    return () => controller.abort();
  }, [selectedWeek, selectedYear]);

  // Games for the currently loaded week. Empty on first load or while a new
  // week/year is being fetched. Deriving from this (instead of early-returning)
  // keeps the filter bar mounted so it never disappears during navigation.
  const games = gameData?.games ?? [];

  // Extract unique conferences, preserving original case for filtering
  const conferenceSet = new Set(
    games
      .flatMap((game) => [game.away.conference, game.home.conference])
      .filter(Boolean) // Remove null/undefined values
  );

  const conferences = [
    { value: "All", label: "All" },
    ...Array.from(conferenceSet)
      .sort()
      .map((conf) => ({
        value: conf,
        label: formatConferenceName(conf),
      })),
  ];

  const statuses = ["All", "Final", "Live", "Upcoming"];

  // Supports all possible weeks returned by getCurrentWeek (1–18)
  const weeks = Array.from({ length: 19 }, (_, i) => i + 1);

  // Year options: current year going back to 2025
  const currentYear = new Date().getFullYear();
  const years = Array.from(
    { length: currentYear - 2025 + 1 },
    (_, i) => currentYear - i
  );

  // Extract unique dates from games
  const dateSet = new Map();
  games.forEach((game) => {
    if (game.epoch) {
      const date = new Date(game.epoch * 1000);
      const dateKey = date.toLocaleDateString("en-US", {
        weekday: "short",
        month: "short",
        day: "numeric",
      });
      // Use YYYY-MM-DD as the value for easy comparison
      const dateValue = date.toISOString().split("T")[0];
      if (!dateSet.has(dateKey)) {
        dateSet.set(dateKey, dateValue);
      }
    }
  });

  const dates = [
    { value: "All", label: "All Dates" },
    ...Array.from(dateSet.entries())
      .sort(([, a], [, b]) => a.localeCompare(b))
      .map(([label, value]) => ({ value, label })),
  ];

  // Filter scores based on selected filters
  const filteredScores = games.filter((game) => {
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
    const dateMatch =
      selectedDate === "All" ||
      !game.epoch ||
      new Date(game.epoch * 1000).toISOString().split("T")[0] === selectedDate;
    return conferenceMatch && statusMatch && dateMatch;
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
            {/* Year Dropdown */}
            <div className={styles.homePageFilterGroup}>
              <label className={styles.homePageFilterLabel}>Year:</label>
              <select
                className={styles.homePageFilterSelect}
                value={selectedYear}
                onChange={(e) => setSelectedYear(Number(e.target.value))}
              >
                {years.map((year) => (
                  <option key={year} value={year}>
                    {year}
                  </option>
                ))}
              </select>
            </div>
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

            <div className={styles.homePageFilterGroup}>
              <label className={styles.homePageFilterLabel}>Date:</label>
              <select
                className={styles.homePageFilterSelect}
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
              >
                {dates.map((date) => (
                  <option key={date.value} value={date.value}>
                    {date.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Scores grouped by date to make it easier to scan */}
          <section className={styles.homePageSection}>
            {loading && (
              <div className={styles.loadingContainer}>
                <LoadingSpinner />
              </div>
            )}

            {!loading && error && (
              <div className={styles.errorContainer}>
                <p>{error}</p>
              </div>
            )}

            {!loading && !error && filteredScores.length === 0 && (
              <div className={styles.homePageNoResults}>
                <p>No scores found matching your filters.</p>
              </div>
            )}

            {!loading &&
              !error &&
              filteredScores.length > 0 &&
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
