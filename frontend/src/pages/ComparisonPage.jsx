import React from "react";
import { useState, useEffect } from "react";
import Header from "../components/Header";
import { appConfig } from "../constants";
import styles from "../styles/pages/ComparisonPage.module.css";
import api from "../services/api";
import LoadingSpinner from "../components/LoadingSpinner";

const ComparisonPage = () => {
  const [selectedTeamA, setSelectedTeamA] = useState(null);
  const [selectedTeamB, setSelectedTeamB] = useState(null);
  const [teamAData, setTeamAData] = useState(null);
  const [teamBData, setTeamBData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSearch = (searchTerm) => {
    // MOCK FUNCTIONALITY - Replace with actual search API call
    console.log("Searching for:", searchTerm);
  };

  const teams = [
    "Select Team", "Georgia", "Alabama", "Washington State", "Arizona"
  ]

  useEffect(() => {
    if (!selectedTeamA || selectedTeamA === "Select Team") return; // case no selection

      const fetchTeamData = async () => {
        setLoading(true);
        setError(null);

        try {
          const response = await api.getTeamData(selectedTeamA);
          if (response.success) {
            setTeamAData(response.data);    
            console.log(response.data); // debugging purposes
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
    }, [selectedTeamA]);  
  

  useEffect(() => {
    if (!selectedTeamB || selectedTeamB === "Select Team") return; // case no selection

      const fetchTeamData = async () => {
        setLoading(true);
        setError(null);

        try {
          const response = await api.getTeamData(selectedTeamB);
          if (response.success) {
            setTeamBData(response.data);    
            console.log(response.data); // debugging purposes
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
    }, [selectedTeamB]); 

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
            <div className={styles.comparisonPageFilterGrid}>

              {/* Team A Dropdown */}
              <div className={styles.comparisonPageFilterGroup}>
                <label className={styles.comparisonPageFilterLabel}>
                  Team A:
                </label>
                <select
                  className={styles.comparisonPageFilterSelect}
                  value={selectedTeamA}
                  onChange={(e) => setSelectedTeamA(e.target.value)}
                >
                  {teams.map((team) => (
                    <option key={team} value={team}>
                      {team}
                    </option>
                  ))}
                </select>
              </div>
            
              {/* Team B Dropdown */}
              <div className={styles.comparisonPageFilterGroup}>
                  <label className={styles.comparisonPageFilterLabel}>
                    Team B:
                  </label>
                  <select
                    className={styles.comparisonPageFilterSelect}
                    value={selectedTeamB}
                    onChange={(e) => setSelectedTeamB(e.target.value)}
                  >
                    {teams.map((team) => (
                      <option key={team} value={team}>
                        {team}
                      </option>
                    ))}
                  </select>
              </div>

            </div>
          </div>

          {/* Comparison Section */}
          {teamAData != null && teamBData != null && (
          <section className={styles.comparisonPageSection}>
            <h2> Team Comparison </h2>
            <div className={styles.comparisonPageContent}>

              {/* Team A */}
              <div>
              <h3>{teamAData["School"]}</h3>
              <div><strong>Conference L:</strong> {teamAData["Conference L"]}</div>
              <div><strong>Conference W:</strong> {teamAData["Conference W"]}</div>
              <div><strong>Overall Away:</strong> {teamAData["Overall AWAY"]}</div>
              <div><strong>Overall Home:</strong> {teamAData["Overall HOME"]}</div>
              <div><strong>Overall L:</strong> {teamAData["Overall L"]}</div>
              <div><strong>Overall W:</strong> {teamAData["Overall W"]}</div>
              <div><strong>Overall PA:</strong> {teamAData["Overall PA"]}</div>
              <div><strong>Overall PF:</strong> {teamAData["Overall PF"]}</div>
              <div><strong>Overall Streak:</strong> {teamAData["Overall STREAK"]}</div>
              </div>

              {/* Team B */}
              <div>
              <h3>{teamBData["School"]}</h3>
              <div><strong>Conference L:</strong> {teamBData["Conference L"]}</div>
              <div><strong>Conference W:</strong> {teamBData["Conference W"]}</div>
              <div><strong>Overall Away:</strong> {teamBData["Overall AWAY"]}</div>
              <div><strong>Overall Home:</strong> {teamBData["Overall HOME"]}</div>
              <div><strong>Overall L:</strong> {teamBData["Overall L"]}</div>
              <div><strong>Overall W:</strong> {teamBData["Overall W"]}</div>
              <div><strong>Overall PA:</strong> {teamBData["Overall PA"]}</div>
              <div><strong>Overall PF:</strong> {teamBData["Overall PF"]}</div>
              <div><strong>Overall Streak:</strong> {teamBData["Overall STREAK"]}</div>
              </div>
            </div>
          </section>
          )}
        </div>
      </main>
    </div>
  );
};

export default ComparisonPage;
