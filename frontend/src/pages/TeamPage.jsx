import React from "react";
import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import styles from "../styles/pages/TeamPage.module.css";
import api from "../services/api";
import LoadingSpinner from "../components/LoadingSpinner";
import TeamLogo from "../components/TeamLogo";
import { useTeamBranding } from "../hooks/useTeamBranding";

// The football season currently in scope: a CFB season is named for the year
// it starts in and runs Aug–Jan, so from August we're in the new season, and
// before that the most recent completed season is last year. Matches the
// backend's current_season_year() so the default year uses the rich NCAA feed.
const currentSeason = () => {
  const now = new Date();
  return now.getMonth() >= 7 ? now.getFullYear() : now.getFullYear() - 1;
};

// Local fallback season list (newest first) if the /team/seasons fetch fails.
const fallbackSeasons = () => {
  const years = [];
  for (let y = currentSeason(); y >= 2000; y -= 1) years.push(y);
  return years;
};

const TeamPage = () => {
  const { teamName: encodedTeamName } = useParams();
  const navigate = useNavigate();
  const [teamData, setTeamData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [seasons, setSeasons] = useState(fallbackSeasons);
  const [selectedYear, setSelectedYear] = useState(currentSeason);

  // Decode the team name from URL
  const teamName = encodedTeamName ? decodeURIComponent(encodedTeamName) : null;

  // Populate the year dropdown from the backend (falls back to the local range).
  useEffect(() => {
    let active = true;
    api
      .getSeasons()
      .then((res) => {
        if (active && res?.success && Array.isArray(res.data) && res.data.length) {
          setSeasons(res.data);
        }
      })
      .catch(() => {
        /* keep the fallback list */
      });
    return () => {
      active = false;
    };
  }, []);

  // Fetch team data when the team or the selected year changes.
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
        const response = await api.getTeamData(teamName, selectedYear);
        if (response.success) {
          setTeamData(response.data);
        } else {
          setError(
            response.error || `Failed to fetch data for ${teamName} (${selectedYear})`
          );
          setTeamData(null);
        }
      } catch (err) {
        console.error(err);
        setError(`Unable to load ${selectedYear} data for ${teamName}`);
        setTeamData(null);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [teamName, selectedYear]);

  const yearSelect = (
    <label className={styles.yearPicker}>
      <span className={styles.yearPickerLabel}>Season</span>
      <select
        className={styles.yearSelect}
        value={selectedYear}
        onChange={(e) => setSelectedYear(Number(e.target.value))}
        aria-label="Select season"
      >
        {seasons.map((year) => (
          <option key={year} value={year}>
            {year}
          </option>
        ))}
      </select>
    </label>
  );

  return (
    <div className={styles.teamPage}>
      <main className={styles.teamPageMain}>
        <div className={styles.teamPageContainer}>
          {/* The header (back button + year picker) stays put across states so
              the season can be changed even when a year has no data. */}
          <div className={styles.teamPageHeader}>
            <button className={styles.backButton} onClick={() => navigate(-1)}>
              ← Back
            </button>
            {yearSelect}
          </div>

          {loading ? (
            <div className={styles.loadingContainer}>
              <LoadingSpinner />
            </div>
          ) : error || !teamData ? (
            <div className={styles.errorContainer}>
              <p>{error || "Team not found"}</p>
            </div>
          ) : (
            <section className={styles.teamPageSection}>
              <TeamDetailsCard
                teamData={teamData}
                teamName={teamData["School"]}
                year={selectedYear}
              />
            </section>
          )}
        </div>
      </main>
    </div>
  );
};

// Render a stat value, showing an em dash for anything the source didn't
// provide (CFBD historical records have no points for/against or streak).
const statValue = (v) =>
  v === null || v === undefined || v === "" ? "—" : v;

// Team Details Card Component (similar to TeamComparisonCard but for single team)
const TeamDetailsCard = ({ teamData, teamName, year }) => {
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
        <div>
          <h1 className={styles.teamDetailsTitle}>{teamData["School"]}</h1>
          {year && <div className={styles.teamDetailsSeason}>{year} season</div>}
        </div>
      </div>
      <div className={styles.teamDetailsStats}>
        <div className={styles.teamDetailsStatRow}>
          <strong>Conference Record:</strong> {statValue(teamData["Conference W"])}
          -{statValue(teamData["Conference L"])}
        </div>
        <div className={styles.teamDetailsStatRow}>
          <strong>Overall Record:</strong> {statValue(teamData["Overall W"])}-
          {statValue(teamData["Overall L"])}
        </div>
        <div className={styles.teamDetailsStatRow}>
          <strong>Points For:</strong> {statValue(teamData["Overall PF"])}
        </div>
        <div className={styles.teamDetailsStatRow}>
          <strong>Points Against:</strong> {statValue(teamData["Overall PA"])}
        </div>
        <div className={styles.teamDetailsStatRow}>
          <strong>Home Record:</strong> {statValue(teamData["Overall HOME"])}
        </div>
        <div className={styles.teamDetailsStatRow}>
          <strong>Away Record:</strong> {statValue(teamData["Overall AWAY"])}
        </div>
        <div className={styles.teamDetailsStatRow}>
          <strong>Current Streak:</strong> {statValue(teamData["Overall STREAK"])}
        </div>
      </div>
    </div>
  );
};

export default TeamPage;
