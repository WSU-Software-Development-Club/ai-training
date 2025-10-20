import React from "react";
import Header from "../components/Header";
import TeamCard from "../components/TeamCard";
import { appConfig } from "../constants";
import { mockTeams } from "../utils/mockData";
import "../styles/pages/TeamsPage.css";

const TeamsPage = () => {
  const handleSearch = (searchTerm) => {
    // MOCK FUNCTIONALITY - Replace with actual search API call
    console.log("Searching for:", searchTerm);
  };

  return (
    <div className="teams-page">
      <Header title={appConfig.name} onSearch={handleSearch} />

      <main className="teams-page__main">
        <div className="teams-page__container">
          <div className="teams-page__header">
            <h1 className="teams-page__title">College Football Teams</h1>
            <p className="teams-page__subtitle">
              Browse all FBS college football teams
            </p>
          </div>

          <div className="teams-page__content">
            <div className="teams-page__teams-grid">
              {mockTeams.map((team) => (
                <TeamCard key={team.id} team={team} />
              ))}
            </div>

            {/* TODO: Replace mockTeams with API call to /api/teams */}
            {/* Hint: Use useState, useEffect, and fetch API */}
          </div>
        </div>
      </main>
    </div>
  );
};

export default TeamsPage;
