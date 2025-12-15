import React from "react";
import { useState, useEffect } from "react";
import Header from "../components/Header";
import { appConfig } from "../constants";
import styles from "../styles/pages/ComparisonPage.module.css";
import api from "../services/api";
import LoadingSpinner from "../components/LoadingSpinner";

const ComparisonPage = () => {
  const [teams, setTeams] = useState([]);
  const [teamsLoading, setTeamsLoading] = useState(true);
  const [selectedTeamA, setSelectedTeamA] = useState("Select Team");
  const [selectedTeamB, setSelectedTeamB] = useState("Select Team");
  const [teamAData, setTeamAData] = useState(null);
  const [teamBData, setTeamBData] = useState(null);
  const [loadingA, setLoadingA] = useState(false);
  const [loadingB, setLoadingB] = useState(false);
  const [errorA, setErrorA] = useState(null);
  const [errorB, setErrorB] = useState(null);

  const handleSearch = (searchTerm) => {
    // MOCK FUNCTIONALITY - Replace with actual search API call
    console.log("Searching for:", searchTerm);
  };

  // Fetch teams list on component mount
  useEffect(() => {
    const fetchTeams = async () => {
      setTeamsLoading(true);
      try {
        const response = await api.getAllTeams();
        if (response.success && response.data) {
          // Sort teams alphabetically by name
          const sortedTeams = [...response.data].sort((a, b) =>
            a.name.localeCompare(b.name)
          );
          setTeams(sortedTeams);
        } else {
          console.error("Failed to fetch teams:", response.error);
          // Fallback to empty array - will show error in UI
          setTeams([]);
        }
      } catch (err) {
        console.error("Error fetching teams:", err);
        setTeams([]);
      } finally {
        setTeamsLoading(false);
      }
    };

    fetchTeams();
  }, []);

  // Fetch team A data when selected
  useEffect(() => {
    if (!selectedTeamA || selectedTeamA === "Select Team") {
      setTeamAData(null);
      setErrorA(null);
      return;
    }

    const fetchData = async () => {
      setLoadingA(true);
      setErrorA(null);

      try {
        const response = await api.getTeamData(selectedTeamA);
        if (response.success) {
          setTeamAData(response.data);
        } else {
          setErrorA(
            response.error || `Failed to fetch data for ${selectedTeamA}`
          );
          setTeamAData(null);
        }
      } catch (err) {
        console.error(err);
        setErrorA(`Unable to load data for ${selectedTeamA}`);
        setTeamAData(null);
      } finally {
        setLoadingA(false);
      }
    };

    fetchData();
  }, [selectedTeamA]);

  // Fetch team B data when selected
  useEffect(() => {
    if (!selectedTeamB || selectedTeamB === "Select Team") {
      setTeamBData(null);
      setErrorB(null);
      return;
    }

    const fetchData = async () => {
      setLoadingB(true);
      setErrorB(null);

      try {
        const response = await api.getTeamData(selectedTeamB);
        if (response.success) {
          setTeamBData(response.data);
        } else {
          setErrorB(
            response.error || `Failed to fetch data for ${selectedTeamB}`
          );
          setTeamBData(null);
        }
      } catch (err) {
        console.error(err);
        setErrorB(`Unable to load data for ${selectedTeamB}`);
        setTeamBData(null);
      } finally {
        setLoadingB(false);
      }
    };

    fetchData();
  }, [selectedTeamB]);

  // Handle team selection with validation
  const handleTeamAChange = (e) => {
    const value = e.target.value;
    if (value === selectedTeamB && value !== "Select Team") {
      // Prevent selecting the same team
      alert("Please select a different team for Team B");
      return;
    }
    setSelectedTeamA(value);
  };

  const handleTeamBChange = (e) => {
    const value = e.target.value;
    if (value === selectedTeamA && value !== "Select Team") {
      // Prevent selecting the same team
      alert("Please select a different team for Team A");
      return;
    }
    setSelectedTeamB(value);
  };

  // Get team names for dropdowns (filter out the selected team from the other dropdown)
  const getAvailableTeamsForA = () => {
    return teams.filter((team) => team.name !== selectedTeamB);
  };

  const getAvailableTeamsForB = () => {
    return teams.filter((team) => team.name !== selectedTeamA);
  };

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
            <div className={styles.comparisonPageFilterGrid}>
              {/* Team A Dropdown */}
              <div className={styles.comparisonPageFilterGroup}>
                <label className={styles.comparisonPageFilterLabel}>
                  Team A:
                </label>
                {teamsLoading ? (
                  <div className={styles.loadingContainer}>
                    <LoadingSpinner />
                  </div>
                ) : (
                  <select
                    className={styles.comparisonPageFilterSelect}
                    value={selectedTeamA}
                    onChange={handleTeamAChange}
                    disabled={teamsLoading || teams.length === 0}
                  >
                    <option value="Select Team">Select Team</option>
                    {getAvailableTeamsForA().map((team) => (
                      <option key={team.id || team.name} value={team.name}>
                        {team.name}
                      </option>
                    ))}
                  </select>
                )}
                {loadingA && (
                  <div className={styles.teamLoadingIndicator}>
                    Loading team data...
                  </div>
                )}
                {errorA && (
                  <div className={styles.teamErrorIndicator}>{errorA}</div>
                )}
              </div>

              {/* Team B Dropdown */}
              <div className={styles.comparisonPageFilterGroup}>
                <label className={styles.comparisonPageFilterLabel}>
                  Team B:
                </label>
                {teamsLoading ? (
                  <div className={styles.loadingContainer}>
                    <LoadingSpinner />
                  </div>
                ) : (
                  <select
                    className={styles.comparisonPageFilterSelect}
                    value={selectedTeamB}
                    onChange={handleTeamBChange}
                    disabled={teamsLoading || teams.length === 0}
                  >
                    <option value="Select Team">Select Team</option>
                    {getAvailableTeamsForB().map((team) => (
                      <option key={team.id || team.name} value={team.name}>
                        {team.name}
                      </option>
                    ))}
                  </select>
                )}
                {loadingB && (
                  <div className={styles.teamLoadingIndicator}>
                    Loading team data...
                  </div>
                )}
                {errorB && (
                  <div className={styles.teamErrorIndicator}>{errorB}</div>
                )}
              </div>
            </div>
          </div>

          {/* Teams loading error */}
          {!teamsLoading && teams.length === 0 && (
            <div className={styles.errorContainer}>
              <p>Unable to load teams list. Please refresh the page.</p>
            </div>
          )}

          {/* Comparison Section */}
          {teamAData && teamBData && !errorA && !errorB && (
            <section className={styles.comparisonPageSection}>
              <h2>Team Comparison</h2>
              <div className={styles.comparisonPageContent}>
                {/* Team A */}
                <div className={styles.teamComparisonCard}>
                  <h3 className={styles.teamComparisonTitle}>
                    {teamAData["School"]}
                  </h3>
                  <div className={styles.teamComparisonStats}>
                    <div className={styles.teamComparisonStatRow}>
                      <strong>Conference Record:</strong>{" "}
                      {teamAData["Conference W"]}-{teamAData["Conference L"]}
                    </div>
                    <div className={styles.teamComparisonStatRow}>
                      <strong>Overall Record:</strong> {teamAData["Overall W"]}-
                      {teamAData["Overall L"]}
                    </div>
                    <div className={styles.teamComparisonStatRow}>
                      <strong>Points For:</strong> {teamAData["Overall PF"]}
                    </div>
                    <div className={styles.teamComparisonStatRow}>
                      <strong>Points Against:</strong> {teamAData["Overall PA"]}
                    </div>
                    <div className={styles.teamComparisonStatRow}>
                      <strong>Home Record:</strong> {teamAData["Overall HOME"]}
                    </div>
                    <div className={styles.teamComparisonStatRow}>
                      <strong>Away Record:</strong> {teamAData["Overall AWAY"]}
                    </div>
                    <div className={styles.teamComparisonStatRow}>
                      <strong>Current Streak:</strong>{" "}
                      {teamAData["Overall STREAK"]}
                    </div>
                  </div>
                </div>

                {/* Team B */}
                <div className={styles.teamComparisonCard}>
                  <h3 className={styles.teamComparisonTitle}>
                    {teamBData["School"]}
                  </h3>
                  <div className={styles.teamComparisonStats}>
                    <div className={styles.teamComparisonStatRow}>
                      <strong>Conference Record:</strong>{" "}
                      {teamBData["Conference W"]}-{teamBData["Conference L"]}
                    </div>
                    <div className={styles.teamComparisonStatRow}>
                      <strong>Overall Record:</strong> {teamBData["Overall W"]}-
                      {teamBData["Overall L"]}
                    </div>
                    <div className={styles.teamComparisonStatRow}>
                      <strong>Points For:</strong> {teamBData["Overall PF"]}
                    </div>
                    <div className={styles.teamComparisonStatRow}>
                      <strong>Points Against:</strong> {teamBData["Overall PA"]}
                    </div>
                    <div className={styles.teamComparisonStatRow}>
                      <strong>Home Record:</strong> {teamBData["Overall HOME"]}
                    </div>
                    <div className={styles.teamComparisonStatRow}>
                      <strong>Away Record:</strong> {teamBData["Overall AWAY"]}
                    </div>
                    <div className={styles.teamComparisonStatRow}>
                      <strong>Current Streak:</strong>{" "}
                      {teamBData["Overall STREAK"]}
                    </div>
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* Placeholder when no teams selected */}
          {(!teamAData || !teamBData) &&
            !loadingA &&
            !loadingB &&
            !errorA &&
            !errorB &&
            teams.length > 0 && (
              <div className={styles.comparisonPagePlaceholder}>
                <p className={styles.comparisonPagePlaceholderText}>
                  Select two teams above to compare their statistics
                </p>
              </div>
            )}
        </div>
      </main>
    </div>
  );
};

export default ComparisonPage;
