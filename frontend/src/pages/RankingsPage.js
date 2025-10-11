import React from "react";
import Header from "../components/Header";
import RankingsTable from "../components/RankingsTable";
import { appConfig } from "../constants";
import { mockRankings } from "../utils/mockData";
import "../styles/pages/RankingsPage.css";

const RankingsPage = () => {
  const handleSearch = (searchTerm) => {
    // MOCK FUNCTIONALITY - Replace with actual search API call
    console.log("Searching for:", searchTerm);
  };

  return (
    <div className="rankings-page">
      <Header title={appConfig.name} onSearch={handleSearch} />

      <main className="rankings-page__main">
        <div className="rankings-page__container">
          <div className="rankings-page__header">
            <h1 className="rankings-page__title">AP Top 25 Rankings</h1>
            <p className="rankings-page__subtitle">
              Current Associated Press College Football Rankings
            </p>
          </div>

          <div className="rankings-page__content">
            <RankingsTable rankings={mockRankings} title="AP Top 25" />

            {/* TODO: Replace mockRankings with API call to /api/rankings/ap-top25 */}
            {/* Hint: Use useState, useEffect, and fetch API */}
          </div>
        </div>
      </main>
    </div>
  );
};

export default RankingsPage;
