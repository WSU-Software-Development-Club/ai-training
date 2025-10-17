import React, { useState } from "react";
import Header from "../components/Header";
import ScoreCard from "../components/ScoreCard";
import { appConfig } from "../constants";
import { mockScores } from "../utils/mockData";
import { getCurrentWeek } from "../utils/helpers"
import "../styles/pages/HomePage.css";

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
    <div className="home-page">
      <Header title={appConfig.name} onSearch={handleSearch} />

      <main className="home-page__main">
        <div className="home-page__container">
          <div className="home-page__header">
            <h1 className="home-page__title">College Football Scores</h1>
            <p className="home-page__subtitle">
              Latest scores from across all conferences
            </p>
          </div>

          <div className="home-page__filters">
            <div className="home-page__filter-group">
              <label className="home-page__filter-label">Conference:</label>
              <select
                className="home-page__filter-select"
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

            <div className="home-page__filter-group">
              <label className="home-page__filter-label">Status:</label>
              <select
                className="home-page__filter-select"
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
          <section className="home-page__section">
            <div className="home-page__scores-grid">
              {filteredScores.slice(0, 6).map((game) => (
                <ScoreCard key={game.id} game={game} />
              ))}
            </div>

            {filteredScores.length === 0 && (
              <div className="home-page__no-results">
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
