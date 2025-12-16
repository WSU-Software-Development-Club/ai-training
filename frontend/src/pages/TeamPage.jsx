import React from "react";
import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import Header from "../components/Header";
import { appConfig } from "../constants";
import styles from "../styles/pages/TeamPage.module.css";
import api from "../services/api";
import LoadingSpinner from "../components/LoadingSpinner";
import TeamLogo from "../components/TeamLogo";
import { useTeamBranding } from "../hooks/useTeamBranding";

const TeamPage = () => {
  const { teamName: encodedTeamName } = useParams();
  const navigate = useNavigate();
  const [teamData, setTeamData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Decode the team name from URL
  const teamName = encodedTeamName ? decodeURIComponent(encodedTeamName) : null;

  const handleSearch = (searchTerm) => {
    // Search functionality will be handled by Header/SearchBar
    // This is just a placeholder to match the interface
    console.log("Searching for:", searchTerm);
  };

  // Fetch team data when component mounts or teamName changes
  useEffect(() => {
    if (!teamName) {
      setError("No team name provided");
      setLoading(false);
      return;
    }

    const fetchData = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await api.getTeamData(teamName);
        if (response.success) {
          setTeamData(response.data);
        } else {
          setError(response.error || `Failed to fetch data for ${teamName}`);
          setTeamData(null);
        }
      } catch (err) {
        console.error(err);
        setError(`Unable to load data for ${teamName}`);
        setTeamData(null);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [teamName]);

  if (loading) {
    return (
      <div className={styles.teamPage}>
        <Header title={appConfig.name} onSearch={handleSearch} />
        <main className={styles.teamPageMain}>
          <div className={styles.loadingContainer}>
            <LoadingSpinner />
          </div>
        </main>
      </div>
    );
  }

  if (error || !teamData) {
    return (
      <div className={styles.teamPage}>
        <Header title={appConfig.name} onSearch={handleSearch} />
        <main className={styles.teamPageMain}>
          <div className={styles.teamPageContainer}>
            <div className={styles.errorContainer}>
              <p>{error || "Team not found"}</p>
              <button
                className={styles.backButton}
                onClick={() => navigate(-1)}
              >
                Go Back
              </button>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className={styles.teamPage}>
      <Header title={appConfig.name} onSearch={handleSearch} />
      <main className={styles.teamPageMain}>
        <div className={styles.teamPageContainer}>
          <div className={styles.teamPageHeader}>
            <button className={styles.backButton} onClick={() => navigate(-1)}>
              ← Back
            </button>
          </div>

          {/* Team Details Section */}
          <section className={styles.teamPageSection}>
            <TeamDetailsCard
              teamData={teamData}
              teamName={teamData["School"]}
            />
          </section>
        </div>
      </main>
    </div>
  );
};

// Team Details Card Component (similar to TeamComparisonCard but for single team)
const TeamDetailsCard = ({ teamData, teamName }) => {
  const { branding } = useTeamBranding(teamName);

  const cardStyle = branding?.primaryColor
    ? {
        borderTopColor: branding.primaryColor,
        borderTopWidth: "4px",
        borderTopStyle: "solid",
      }
    : {};

  return (
    <div className={styles.teamDetailsCard} style={cardStyle}>
      <div className={styles.teamDetailsHeader}>
        <TeamLogo
          teamName={teamName}
          size="large"
          className={styles.teamDetailsLogo}
        />
        <h1 className={styles.teamDetailsTitle}>{teamData["School"]}</h1>
      </div>
      <div className={styles.teamDetailsStats}>
        <div className={styles.teamDetailsStatRow}>
          <strong>Conference Record:</strong> {teamData["Conference W"]}-
          {teamData["Conference L"]}
        </div>
        <div className={styles.teamDetailsStatRow}>
          <strong>Overall Record:</strong> {teamData["Overall W"]}-
          {teamData["Overall L"]}
        </div>
        <div className={styles.teamDetailsStatRow}>
          <strong>Points For:</strong> {teamData["Overall PF"]}
        </div>
        <div className={styles.teamDetailsStatRow}>
          <strong>Points Against:</strong> {teamData["Overall PA"]}
        </div>
        <div className={styles.teamDetailsStatRow}>
          <strong>Home Record:</strong> {teamData["Overall HOME"]}
        </div>
        <div className={styles.teamDetailsStatRow}>
          <strong>Away Record:</strong> {teamData["Overall AWAY"]}
        </div>
        <div className={styles.teamDetailsStatRow}>
          <strong>Current Streak:</strong> {teamData["Overall STREAK"]}
        </div>
      </div>
    </div>
  );
};

export default TeamPage;
