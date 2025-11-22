import React from "react";
import { useState, useEffect } from "react";
import Header from "../components/Header";
import { appConfig } from "../constants";
import styles from "../styles/pages/ComparisonPage.module.css";
import api from "../services/api";
import LoadingSpinner from "../components/LoadingSpinner";

const ComparisonPage = () => {
  const [selectedTeam, setSelectedTeam] = useState(null); 
  const [selectedTeamA, setSelectedTeamA] = useState(null);
  const [selectedTeamB, setSelectedTeamB] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const handleSearch = (searchTerm) => {
    // MOCK FUNCTIONALITY - Replace with actual search API call
    console.log("Searching for:", searchTerm);
  };

  const teams = [
    "None", "Georgia", "Alabama"
  ]

  useEffect(() => {
      const fetchTeamData = async () => {
        setLoading(true);
        setError(null);

        try {
          const response = await api.getTeamData("Georgia");
          if (response.success) {
            setSelectedTeam(response.data);    
            console.log(response.data)
          } else {
            setError("No team data available.");
          }
        } catch (err) {
          console.error(err);
          setError("Unable to load team data.");
        } finally {
          setLoading(false);
        }
      };
  
      fetchTeamData();
    }, ["Georgia"]);  
  
    if (loading) {
    return (
      <div className={styles.comparisonPage}>
        <Header title={appConfig.name} onSearch={handleSearch} />
        <main className={styles.comparisonPageMain}>
          <div className={styles.loadingContainer}>
            <LoadingSpinner />
          </div>
        </main>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.comparisonPage}>
        <Header title={appConfig.name} onSearch={handleSearch} />
        <main className={styles.comparisonPageMain}>
          <div className={styles.errorContainer}>
            <p>{error}</p>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className={styles.comparisonPage}>
      <Header title={appConfig.name} onSearch={handleSearch} />

      <main className={styles.comparisonPageMain}>
        <div className={styles.comparisonPageContainer}>
          <div className={styles.comparisonPageHeader}>
            <h1 className={styles.comparisonPageTitle}>Team Comparison</h1>
            <p className={styles.comparisonPageSubtitle}>
              Compare statistics between college football teams
            </p>
          </div>

          {/* Team Filter Section */}
          <div className={styles.comparisonPageFilters}>
            <h2> Team Filters </h2>

            <div className={styles.comparisonPageGrid}>
              {/* Team Dropdown */}
              <div className={styles.comparisonPageFilterGroup}>
                <label className={styles.comparisonPageFilterLabel}>
                  Team:
                </label>
                <select
                  className={styles.comparisonPageFilterSelect}
                  value={selectedTeam}
                  onChange={(e) => setSelectedTeam(e.target.value)}
                >
                  {teams.map((team) => (
                    <option key={team} value={team}>
                      Team {team}
                    </option>
                  ))}
                </select>
              </div>
            
              {/* Team 2 Dropdown */}
              <div className={styles.comparisonPageFilterGroup}>
                  <label className={styles.comparisonPageFilterLabel}>
                    Team:
                  </label>
                  <select
                    className={styles.comparisonPageFilterSelect}
                    value={selectedTeam}
                    onChange={(e) => setSelectedTeam(e.target.value)}
                  >
                    {teams.map((team) => (
                      <option key={team} value={team}>
                        Team {team}
                      </option>
                    ))}
                  </select>
                </div>
            </div>
          </div>
          <section className={styles.comparisonPageSection}>
            <div className={styles.comparisonPageGrid}>
              {error && <p className="error">{error}</p>}
              {
                
              }
            </div>
          </section>
        </div>
      </main>
    </div>
  );
};

export default ComparisonPage;
