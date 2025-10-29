import React, { useState } from "react";
import Header from "../components/Header";
import ScoreCard from "../components/ScoreCard";
import { appConfig } from "../constants";
import { mockScores } from "../utils/mockData";
import styles from "../styles/pages/ScoresPage.module.css";

const ScoresPage = () => {
  const [selectedConference, setSelectedConference] = useState("All");
  const [selectedStatus, setSelectedStatus] = useState("All");

  const handleSearch = (searchTerm) => {
    // TODO: Replace with API call to /api/search
    console.log("Searching for:", searchTerm);
  };

  // Get unique conferences from mock data
  const conferences = [
    "All",
    ...new Set(mockScores.map((game) => game.conference)),
  ];
  const statuses = ["All", "Final", "Live", "Upcoming"];

  // Filter scores based on selected filters
  const filteredScores = mockScores.filter((game) => {
    const conferenceMatch =
      selectedConference === "All" || game.conference === selectedConference;
    const statusMatch =
      selectedStatus === "All" || game.status === selectedStatus;
    return conferenceMatch && statusMatch;
  });

  return (
    <div className={styles.scoresPage}>
      <Header title={appConfig.name} onSearch={handleSearch} />

      <main className={styles.scoresPageMain}>
        <div className={styles.scoresPageContainer}>
          <div className={styles.scoresPageHeader}>
            <h1 className={styles.scoresPageTitle}>College Football Scores</h1>
            <p className={styles.scoresPageSubtitle}>
              Filter and view scores by conference and status
            </p>
          </div>

          <div className={styles.scoresPageFilters}>
            <div className={styles.scoresPageFilterGroup}>
              <label className={styles.scoresPageFilterLabel}>
                Conference:
              </label>
              <select
                className={styles.scoresPageFilterSelect}
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

            <div className={styles.scoresPageFilterGroup}>
              <label className={styles.scoresPageFilterLabel}>Status:</label>
              <select
                className={styles.scoresPageFilterSelect}
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

          <div className={styles.scoresPageContent}>
            <div className={styles.scoresPageScoresGrid}>
              {filteredScores.map((game) => (
                <ScoreCard key={game.id} game={game} />
              ))}
            </div>

            {filteredScores.length === 0 && (
              <div className={styles.scoresPageNoResults}>
                <p>No scores found matching your filters.</p>
              </div>
            )}

            {/* TODO: Replace mockScores with API call to /api/scores */}
            {/* Hint: Use useState, useEffect, and fetch API */}
          </div>
        </div>
      </main>
    </div>
  );
};

export default ScoresPage;
