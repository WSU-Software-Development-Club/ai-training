import React from "react";
import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import styles from "../styles/pages/ComparisonPage.module.css";
import api from "../services/api";
import LoadingSpinner from "../components/LoadingSpinner";
import { useTeamBranding } from "../hooks/useTeamBranding";
import { navigateToTeam } from "../utils/teamNavigation";

// Keys for remembering the comparison selection for the current tab session.
// sessionStorage (not localStorage) so it clears when the tab is closed.
const STORAGE_KEY_A = "comparison.selectedTeamA";
const STORAGE_KEY_B = "comparison.selectedTeamB";

const readStoredTeam = (key) => {
  try {
    return sessionStorage.getItem(key) || "Select Team";
  } catch {
    return "Select Team";
  }
};

const writeStoredTeam = (key, value) => {
  try {
    if (value && value !== "Select Team") {
      sessionStorage.setItem(key, value);
    } else {
      sessionStorage.removeItem(key);
    }
  } catch {
    // Ignore storage errors (e.g. private mode) — memory is best-effort.
  }
};

const ComparisonPage = () => {
  const [searchParams] = useSearchParams();
  const [teams, setTeams] = useState([]);
  const [teamsLoading, setTeamsLoading] = useState(true);
  // Seed from this session's remembered selection so navigating away and back
  // restores the teams the user had picked.
  const [selectedTeamA, setSelectedTeamA] = useState(() =>
    readStoredTeam(STORAGE_KEY_A)
  );
  const [selectedTeamB, setSelectedTeamB] = useState(() =>
    readStoredTeam(STORAGE_KEY_B)
  );
  const [teamAData, setTeamAData] = useState(null);
  const [teamBData, setTeamBData] = useState(null);
  const [loadingA, setLoadingA] = useState(false);
  const [loadingB, setLoadingB] = useState(false);
  const [errorA, setErrorA] = useState(null);
  const [errorB, setErrorB] = useState(null);

  // Remember the current selection for this session so it survives navigation.
  useEffect(() => {
    writeStoredTeam(STORAGE_KEY_A, selectedTeamA);
  }, [selectedTeamA]);

  useEffect(() => {
    writeStoredTeam(STORAGE_KEY_B, selectedTeamB);
  }, [selectedTeamB]);

  // Fetch teams list on component mount
  useEffect(() => {
    const controller = new AbortController();

    const fetchTeams = async () => {
      setTeamsLoading(true);
      try {
        const response = await api.getAllTeams({ signal: controller.signal });
        if (response.success && response.data) {
          // Sort teams alphabetically by name
          const sortedTeams = [...response.data].sort((a, b) =>
            a.name.localeCompare(b.name)
          );
          setTeams(sortedTeams);

          // Check for URL parameters to pre-select teams
          const teamAFromUrl = searchParams.get("teamA");
          const teamBFromUrl = searchParams.get("teamB");

          if (teamAFromUrl && teamBFromUrl) {
            // Decode team names from URL
            const decodedTeamA = decodeURIComponent(teamAFromUrl);
            const decodedTeamB = decodeURIComponent(teamBFromUrl);

            // Verify teams exist in the list
            const teamAExists = sortedTeams.some(
              (t) => t.name === decodedTeamA
            );
            const teamBExists = sortedTeams.some(
              (t) => t.name === decodedTeamB
            );

            if (teamAExists && teamBExists && decodedTeamA !== decodedTeamB) {
              setSelectedTeamA(decodedTeamA);
              setSelectedTeamB(decodedTeamB);
            }
          }
        } else {
          console.error("Failed to fetch teams:", response.error);
          // Fallback to empty array - will show error in UI
          setTeams([]);
        }
      } catch (err) {
        if (err.name === "AbortError") return;
        console.error("Error fetching teams:", err);
        setTeams([]);
      } finally {
        if (!controller.signal.aborted) {
          setTeamsLoading(false);
        }
      }
    };

    fetchTeams();

    return () => controller.abort();
  }, [searchParams]);

  // Fetch team A data when selected
  useEffect(() => {
    if (!selectedTeamA || selectedTeamA === "Select Team") {
      setTeamAData(null);
      setErrorA(null);
      return;
    }

    const controller = new AbortController();

    const fetchData = async () => {
      setLoadingA(true);
      setErrorA(null);

      try {
        const response = await api.getTeamData(selectedTeamA, {
          signal: controller.signal,
        });
        if (response.success) {
          setTeamAData(response.data);
        } else {
          setErrorA(
            response.error || `Failed to fetch data for ${selectedTeamA}`
          );
          setTeamAData(null);
        }
      } catch (err) {
        if (err.name === "AbortError") return;
        console.error(err);
        setErrorA(`Unable to load data for ${selectedTeamA}`);
        setTeamAData(null);
      } finally {
        if (!controller.signal.aborted) {
          setLoadingA(false);
        }
      }
    };

    fetchData();

    return () => controller.abort();
  }, [selectedTeamA]);

  // Fetch team B data when selected
  useEffect(() => {
    if (!selectedTeamB || selectedTeamB === "Select Team") {
      setTeamBData(null);
      setErrorB(null);
      return;
    }

    const controller = new AbortController();

    const fetchData = async () => {
      setLoadingB(true);
      setErrorB(null);

      try {
        const response = await api.getTeamData(selectedTeamB, {
          signal: controller.signal,
        });
        if (response.success) {
          setTeamBData(response.data);
        } else {
          setErrorB(
            response.error || `Failed to fetch data for ${selectedTeamB}`
          );
          setTeamBData(null);
        }
      } catch (err) {
        if (err.name === "AbortError") return;
        console.error(err);
        setErrorB(`Unable to load data for ${selectedTeamB}`);
        setTeamBData(null);
      } finally {
        if (!controller.signal.aborted) {
          setLoadingB(false);
        }
      }
    };

    fetchData();

    return () => controller.abort();
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

  // Both teams must be picked before we consider the comparison to be "loading".
  // A single selection fetches its data in the background without a spinner.
  const bothTeamsSelected =
    selectedTeamA !== "Select Team" && selectedTeamB !== "Select Team";
  const comparisonLoading =
    bothTeamsSelected && (loadingA || loadingB) && !errorA && !errorB;

  return (
    <div className={styles.comparisonPage}>
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
                <select
                  className={styles.comparisonPageFilterSelect}
                  value={teamsLoading ? "" : selectedTeamA}
                  onChange={handleTeamAChange}
                  disabled={teamsLoading || teams.length === 0}
                >
                  {teamsLoading ? (
                    <option value="">Loading teams…</option>
                  ) : (
                    <>
                      <option value="Select Team">Select Team</option>
                      {getAvailableTeamsForA().map((team) => (
                        <option key={team.id || team.name} value={team.name}>
                          {team.name}
                        </option>
                      ))}
                    </>
                  )}
                </select>
                {errorA && (
                  <div className={styles.teamErrorIndicator}>{errorA}</div>
                )}
              </div>

              {/* Team B Dropdown */}
              <div className={styles.comparisonPageFilterGroup}>
                <label className={styles.comparisonPageFilterLabel}>
                  Team B:
                </label>
                <select
                  className={styles.comparisonPageFilterSelect}
                  value={teamsLoading ? "" : selectedTeamB}
                  onChange={handleTeamBChange}
                  disabled={teamsLoading || teams.length === 0}
                >
                  {teamsLoading ? (
                    <option value="">Loading teams…</option>
                  ) : (
                    <>
                      <option value="Select Team">Select Team</option>
                      {getAvailableTeamsForB().map((team) => (
                        <option key={team.id || team.name} value={team.name}>
                          {team.name}
                        </option>
                      ))}
                    </>
                  )}
                </select>
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

          {/* Single unified loading state: teams list, or the comparison
              once BOTH teams are selected. */}
          {(teamsLoading || comparisonLoading) && (
            <div className={styles.comparisonPageLoading}>
              <LoadingSpinner inline />
              <p className={styles.comparisonPageLoadingText}>
                {teamsLoading
                  ? "Loading teams…"
                  : "Loading team comparison…"}
              </p>
            </div>
          )}

          {/* Comparison Section */}
          {teamAData &&
            teamBData &&
            !errorA &&
            !errorB &&
            !loadingA &&
            !loadingB && (
              <section className={styles.comparisonPageSection}>
                <h2>Team Comparison</h2>
                <TeamComparisonTable
                  teamAData={teamAData}
                  teamBData={teamBData}
                />
              </section>
            )}

          {/* Placeholder when both teams aren't selected yet. Stays visible
              while a single team's data loads in the background. */}
          {(!teamAData || !teamBData) &&
            !teamsLoading &&
            !comparisonLoading &&
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

// Helper function to parse win-loss record
const parseRecord = (record) => {
  if (!record || typeof record !== "string") return { wins: 0, losses: 0 };
  const parts = record.split("-");
  return {
    wins: parseInt(parts[0]) || 0,
    losses: parseInt(parts[1]) || 0,
  };
};

// Helper function to parse streak (e.g., "W3", "L2", "W1")
const parseStreak = (streak) => {
  if (!streak || typeof streak !== "string") return { isWin: false, count: 0 };
  const trimmed = streak.trim().toUpperCase();
  const isWin = trimmed.startsWith("W");
  const count = parseInt(trimmed.substring(1)) || 0;
  return { isWin, count };
};

// Helper function to compare records and return win percentage
const compareRecords = (recordA, recordB) => {
  const parsedA = parseRecord(recordA);
  const parsedB = parseRecord(recordB);

  const totalA = parsedA.wins + parsedA.losses;
  const totalB = parsedB.wins + parsedB.losses;

  if (totalA === 0 && totalB === 0) return null;
  if (totalA === 0) return "B";
  if (totalB === 0) return "A";

  const winPctA = parsedA.wins / totalA;
  const winPctB = parsedB.wins / totalB;

  if (winPctA > winPctB) return "A";
  if (winPctB > winPctA) return "B";

  // If win percentage is equal, prefer more wins
  if (parsedA.wins > parsedB.wins) return "A";
  if (parsedB.wins > parsedA.wins) return "B";

  return null; // Tie
};

// Helper function to compare streaks
const compareStreaks = (streakA, streakB) => {
  const parsedA = parseStreak(streakA);
  const parsedB = parseStreak(streakB);

  // Win streaks are better than loss streaks
  if (parsedA.isWin && !parsedB.isWin) return "A";
  if (!parsedA.isWin && parsedB.isWin) return "B";

  // If both are wins or both are losses, compare count
  if (parsedA.isWin && parsedB.isWin) {
    // Longer win streak is better
    if (parsedA.count > parsedB.count) return "A";
    if (parsedB.count > parsedA.count) return "B";
  } else {
    // Shorter loss streak is better (less losses)
    if (parsedA.count < parsedB.count) return "A";
    if (parsedB.count < parsedA.count) return "B";
  }

  return null; // Tie
};

// Helper function to determine which team has better stat
const getBetterTeam = (valueA, valueB, higherIsBetter = true) => {
  const numA = typeof valueA === "string" ? parseFloat(valueA) : valueA;
  const numB = typeof valueB === "string" ? parseFloat(valueB) : valueB;

  if (isNaN(numA) || isNaN(numB)) return null;

  if (higherIsBetter) {
    if (numA > numB) return "A";
    if (numB > numA) return "B";
  } else {
    if (numA < numB) return "A";
    if (numB < numA) return "B";
  }
  return null; // Tie
};

// Team Comparison Table Component
const TeamComparisonTable = ({ teamAData, teamBData }) => {
  const navigate = useNavigate();
  const { branding: brandingA } = useTeamBranding(teamAData["School"]);
  const { branding: brandingB } = useTeamBranding(teamBData["School"]);

  const handleTeamClick = (teamName) => {
    navigateToTeam(navigate, teamName);
  };

  // Calculate win percentages for records
  const confRecordA = parseRecord(
    `${teamAData["Conference W"]}-${teamAData["Conference L"]}`
  );
  const confRecordB = parseRecord(
    `${teamBData["Conference W"]}-${teamBData["Conference L"]}`
  );
  const overallRecordA = parseRecord(
    `${teamAData["Overall W"]}-${teamAData["Overall L"]}`
  );
  const overallRecordB = parseRecord(
    `${teamBData["Overall W"]}-${teamBData["Overall L"]}`
  );

  const confWinPctA =
    confRecordA.wins + confRecordA.losses > 0
      ? confRecordA.wins / (confRecordA.wins + confRecordA.losses)
      : 0;
  const confWinPctB =
    confRecordB.wins + confRecordB.losses > 0
      ? confRecordB.wins / (confRecordB.wins + confRecordB.losses)
      : 0;
  const overallWinPctA =
    overallRecordA.wins + overallRecordA.losses > 0
      ? overallRecordA.wins / (overallRecordA.wins + overallRecordA.losses)
      : 0;
  const overallWinPctB =
    overallRecordB.wins + overallRecordB.losses > 0
      ? overallRecordB.wins / (overallRecordB.wins + overallRecordB.losses)
      : 0;

  const teamAStyle = brandingA?.primaryColor
    ? {
        backgroundColor: `${brandingA.primaryColor}15`,
        borderColor: brandingA.primaryColor,
      }
    : {};

  const teamBStyle = brandingB?.primaryColor
    ? {
        backgroundColor: `${brandingB.primaryColor}15`,
        borderColor: brandingB.primaryColor,
      }
    : {};

  // Header styling that mirrors the ScoreCard aesthetic: the team color with a
  // diagonal lighting sheen, plus the team logo exposed as a CSS custom
  // property so it can be painted as a faint watermark backdrop (see
  // .comparisonTeamHeader::before).
  const buildHeaderStyle = (branding) => {
    const style = { color: "#ffffff" };
    const logo = branding?.logoDark || branding?.logo;
    if (branding?.primaryColor) {
      style.backgroundColor = branding.primaryColor;
      style.backgroundImage =
        "linear-gradient(135deg, rgba(255, 255, 255, 0.2), rgba(255, 255, 255, 0) 42%, rgba(0, 0, 0, 0.3))";
    }
    if (logo) {
      style["--team-logo"] = `url("${logo}")`;
    }
    return style;
  };

  const teamAHeaderStyle = buildHeaderStyle(brandingA);
  const teamBHeaderStyle = buildHeaderStyle(brandingB);

  const comparisonRows = [
    {
      label: "Conference Record",
      valueA: `${teamAData["Conference W"]}-${teamAData["Conference L"]}`,
      valueB: `${teamBData["Conference W"]}-${teamBData["Conference L"]}`,
      betterTeam: getBetterTeam(confWinPctA, confWinPctB),
    },
    {
      label: "Overall Record",
      valueA: `${teamAData["Overall W"]}-${teamAData["Overall L"]}`,
      valueB: `${teamBData["Overall W"]}-${teamBData["Overall L"]}`,
      betterTeam: getBetterTeam(overallWinPctA, overallWinPctB),
    },
    {
      label: "Points For",
      valueA: teamAData["Overall PF"],
      valueB: teamBData["Overall PF"],
      betterTeam: getBetterTeam(
        teamAData["Overall PF"],
        teamBData["Overall PF"]
      ),
    },
    {
      label: "Points Against",
      valueA: teamAData["Overall PA"],
      valueB: teamBData["Overall PA"],
      betterTeam: getBetterTeam(
        teamAData["Overall PA"],
        teamBData["Overall PA"],
        false
      ),
    },
    {
      label: "Home Record",
      valueA: teamAData["Overall HOME"],
      valueB: teamBData["Overall HOME"],
      betterTeam: compareRecords(
        teamAData["Overall HOME"],
        teamBData["Overall HOME"]
      ),
    },
    {
      label: "Away Record",
      valueA: teamAData["Overall AWAY"],
      valueB: teamBData["Overall AWAY"],
      betterTeam: compareRecords(
        teamAData["Overall AWAY"],
        teamBData["Overall AWAY"]
      ),
    },
    {
      label: "Current Streak",
      valueA: teamAData["Overall STREAK"],
      valueB: teamBData["Overall STREAK"],
      betterTeam: compareStreaks(
        teamAData["Overall STREAK"],
        teamBData["Overall STREAK"]
      ),
    },
  ];

  return (
    <div className={styles.comparisonTable}>
      <div className={styles.comparisonTableHeader}>
        <div className={styles.comparisonTeamHeader} style={teamAHeaderStyle}>
          <h3
            className={styles.comparisonTeamName}
            onClick={() => handleTeamClick(teamAData["School"])}
            style={{ cursor: "pointer" }}
          >
            {teamAData["School"]}
          </h3>
        </div>
        <div className={styles.comparisonVs}>VS</div>
        <div className={styles.comparisonTeamHeader} style={teamBHeaderStyle}>
          <h3
            className={styles.comparisonTeamName}
            onClick={() => handleTeamClick(teamBData["School"])}
            style={{ cursor: "pointer" }}
          >
            {teamBData["School"]}
          </h3>
        </div>
      </div>

      <div className={styles.comparisonTableBody}>
        {comparisonRows.map((row, index) => (
          <div key={index} className={styles.comparisonRow}>
            <div className={styles.comparisonRowLabel}>{row.label}</div>
            <div
              className={`${styles.comparisonRowValue} ${
                row.betterTeam === "A" ? styles.comparisonRowWinner : ""
              }`}
              style={row.betterTeam === "A" ? teamAStyle : {}}
            >
              {row.valueA}
              {row.betterTeam === "A" && (
                <span className={styles.comparisonWinnerBadge}>✓</span>
              )}
            </div>
            <div
              className={`${styles.comparisonRowValue} ${
                row.betterTeam === "B" ? styles.comparisonRowWinner : ""
              }`}
              style={row.betterTeam === "B" ? teamBStyle : {}}
            >
              {row.valueB}
              {row.betterTeam === "B" && (
                <span className={styles.comparisonWinnerBadge}>✓</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ComparisonPage;
