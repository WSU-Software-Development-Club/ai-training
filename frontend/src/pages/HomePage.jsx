import React, { useState } from "react";
import Header from "../components/Header";
import ScoreCard from "../components/ScoreCard";
import { appConfig } from "../constants";
import { mockScores } from "../utils/mockData";
import styles from "../styles/pages/HomePage.module.css";

const HomePage = () => {
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
              {filteredScores.slice(0, 6).map((game) => (
                <ScoreCard key={game.id} game={game} />
              ))}
            </div>

            {filteredScores.length === 0 && (
              <div className={styles.homePageNoResults}>
                <p>No scores found matching your filters.</p>
              </div>
            )}

            {/* TODO: Replace mockScores with API call to /api/scores */}
            {/* Hint: Use useState, useEffect, and fetch API */}
          </section>
        </div>
      </main>
    </div>
  );
};

export default HomePage;
