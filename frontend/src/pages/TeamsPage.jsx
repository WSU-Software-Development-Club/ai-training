import React from "react";
import Header from "../components/Header";
import TeamCard from "../components/TeamCard";
import { appConfig } from "../constants";
import { mockTeams } from "../utils/mockData";
import styles from "../styles/pages/TeamsPage.module.css";

const TeamsPage = () => {
  const handleSearch = (searchTerm) => {
    // MOCK FUNCTIONALITY - Replace with actual search API call
    console.log("Searching for:", searchTerm);
  };

  return (
    <div className={styles.teamsPage}>
      <Header title={appConfig.name} onSearch={handleSearch} />

      <main className={styles.teamsPageMain}>
        <div className={styles.teamsPageContainer}>
          <div className={styles.teamsPageHeader}>
            <h1 className={styles.teamsPageTitle}>College Football Teams</h1>
            <p className={styles.teamsPageSubtitle}>
              Browse all FBS college football teams
            </p>
          </div>

          <div className={styles.teamsPageContent}>
            <div className={styles.teamsPageTeamsGrid}>
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
