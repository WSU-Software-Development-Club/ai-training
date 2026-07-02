import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Header from "../components/Header";
import { appConfig } from "../constants";
import api from "../services/api";
import styles from "../styles/pages/TeamsPage.module.css";
import LoadingSpinner from "../components/LoadingSpinner";
import TeamLogo from "../components/TeamLogo";
import { navigateToTeam } from "../utils/teamNavigation";
import { formatConferenceName } from "../utils/helpers";

// Parse a numeric value, defaulting to 0 for blanks/invalid input.
const toNumber = (value) => {
  const parsed = parseFloat(value);
  return Number.isNaN(parsed) ? 0 : parsed;
};

// Convert a "W-L" record string into a win percentage for sorting. Missing
// records sort to the bottom (-1) so teams with data rank above blanks.
const recordWinPct = (record) => {
  if (!record || typeof record !== "string") return -1;
  const [wins, losses] = record.split("-").map((n) => parseInt(n, 10) || 0);
  const total = wins + losses;
  return total > 0 ? wins / total : 0;
};

// Convert a streak like "W3" / "Won 2" / "L1" into a signed number so win
// streaks sort above loss streaks.
const streakValue = (streak) => {
  if (!streak || typeof streak !== "string") return 0;
  const normalized = streak.trim().toUpperCase();
  const count = parseInt(normalized.replace(/[^0-9]/g, ""), 10) || 0;
  if (normalized.startsWith("W")) return count;
  if (normalized.startsWith("L")) return -count;
  return 0;
};

// Column definitions drive both the header row and the sort behavior so the
// two never drift out of sync.
const TEAM_COLUMNS = [
  { key: "name", label: "Team", type: "string", get: (t) => t.name || "" },
  {
    key: "record",
    label: "Overall Record",
    type: "number",
    get: (t) => recordWinPct(t.record),
  },
  {
    key: "conferenceRecord",
    label: "Conf Record",
    type: "number",
    get: (t) => recordWinPct(t.stats?.conferenceRecord),
  },
  {
    key: "pointsPerGame",
    label: "PPG",
    type: "number",
    get: (t) => toNumber(t.stats?.pointsPerGame),
  },
  {
    key: "pointsAllowed",
    label: "PAPG",
    type: "number",
    get: (t) => toNumber(t.stats?.pointsAllowed),
  },
  {
    key: "overallPF",
    label: "PF",
    type: "number",
    get: (t) => toNumber(t.stats?.overallPF),
  },
  {
    key: "overallPA",
    label: "PA",
    type: "number",
    get: (t) => toNumber(t.stats?.overallPA),
  },
  {
    key: "overallHome",
    label: "Home",
    type: "number",
    get: (t) => recordWinPct(t.stats?.overallHome),
  },
  {
    key: "overallAway",
    label: "Away",
    type: "number",
    get: (t) => recordWinPct(t.stats?.overallAway),
  },
  {
    key: "overallStreak",
    label: "Streak",
    type: "number",
    get: (t) => streakValue(t.stats?.overallStreak),
  },
];

const TeamsPage = () => {
  const navigate = useNavigate();
  const [selectedConference, setSelectedConference] = useState("All");
  const [teams, setTeams] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  // Sort state is per-conference (keyed by conference name) so each table
  // sorts independently — clicking a header in one conference must not reorder
  // the others. Shape: { [conference]: { column, direction } }.
  const [sortState, setSortState] = useState({});

  // Toggle direction when re-clicking that conference's active column; otherwise
  // select the new column with a sensible default (A→Z text, highest-first stats).
  const handleSort = (conference, key) => {
    const column = TEAM_COLUMNS.find((c) => c.key === key);
    if (!column) return;

    setSortState((prev) => {
      const current = prev[conference];
      if (current && current.column === key) {
        return {
          ...prev,
          [conference]: {
            column: key,
            direction: current.direction === "asc" ? "desc" : "asc",
          },
        };
      }
      return {
        ...prev,
        [conference]: {
          column: key,
          direction: column.type === "string" ? "asc" : "desc",
        },
      };
    });
  };

  // Return a sorted copy of one conference's teams based on that conference's
  // active column.
  const sortTeams = (teamsToSort, conference) => {
    const state = sortState[conference];
    if (!state || !state.column) return teamsToSort;
    const column = TEAM_COLUMNS.find((c) => c.key === state.column);
    if (!column) return teamsToSort;

    return [...teamsToSort].sort((a, b) => {
      const aValue = column.get(a);
      const bValue = column.get(b);
      const comparison =
        column.type === "string"
          ? String(aValue).localeCompare(String(bValue))
          : aValue - bValue;
      return state.direction === "asc" ? comparison : -comparison;
    });
  };

  const handleSearch = (searchTerm) => {
    // MOCK FUNCTIONALITY - Replace with actual search API call
    console.log("Searching for:", searchTerm);
  };

  useEffect(() => {
    const fetchTeams = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await api.getAllTeams();

        if (response.success) {
          setTeams(response.data);
        } else {
          setError(response.error || "No teams data available.");
        }
      } catch (err) {
        console.error(err);
        setError("Unable to load teams data.");
      } finally {
        setLoading(false);
      }
    };

    fetchTeams();
  }, []);

  // Loaded team list. Empty while the request is in flight — deriving from
  // this (instead of early-returning) keeps the conference filter mounted so
  // it never disappears during loading.
  const teamList = teams ?? [];

  // Extract unique conferences from teams
  const conferenceSet = new Set(
    teamList.map((team) => team.conference).filter(Boolean)
  );

  const conferences = [
    { value: "All", label: "All" },
    ...Array.from(conferenceSet)
      .sort()
      .map((conf) => ({
        value: conf,
        label: formatConferenceName(conf),
      })),
  ];

  // Filter teams based on selected conference
  const filteredTeams = teamList.filter((team) => {
    const conferenceMatch =
      selectedConference === "All" ||
      (team.conference &&
        team.conference.toLowerCase() === selectedConference.toLowerCase());
    return conferenceMatch;
  });

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

          <div className={styles.teamsPageFilters}>
            <div className={styles.teamsPageFilterGroup}>
              <label className={styles.teamsPageFilterLabel}>Conference:</label>
              <select
                className={styles.teamsPageFilterSelect}
                value={selectedConference}
                onChange={(e) => setSelectedConference(e.target.value)}
                disabled={loading}
              >
                {conferences.map((conference) => (
                  <option key={conference.value} value={conference.value}>
                    {conference.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <section className={styles.teamsPageSection}>
            {loading && (
              <div className={styles.loadingContainer}>
                <LoadingSpinner />
              </div>
            )}

            {!loading && error && (
              <div className={styles.errorContainer}>
                <p>{error}</p>
              </div>
            )}

            {!loading && !error && filteredTeams.length === 0 && (
              <div className={styles.teamsPageNoResults}>
                <p>No teams found matching your filters.</p>
              </div>
            )}

            {!loading &&
              !error &&
              filteredTeams.length > 0 &&
              Object.entries(
                filteredTeams.reduce((groups, team) => {
                  const conf = team.conference || "Independent";
                  if (!groups[conf]) {
                    groups[conf] = [];
                  }
                  groups[conf].push(team);
                  return groups;
                }, {})
              )
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([conference, teams]) => (
                  <div
                    key={conference}
                    className={styles.teamsPageConferenceGroup}
                  >
                    <h2 className={styles.teamsPageConferenceHeading}>
                      {formatConferenceName(conference)}
                    </h2>
                    <div className={styles.teamsPageTableContainer}>
                      <table className={styles.teamsPageTable}>
                        <thead>
                          <tr>
                            {TEAM_COLUMNS.map((column) => {
                              const state = sortState[conference];
                              const isActive = state?.column === column.key;
                              return (
                                <th
                                  key={column.key}
                                  className={`${styles.teamsPageTableHeader} ${styles.teamsPageTableHeaderSortable}`}
                                  onClick={() =>
                                    handleSort(conference, column.key)
                                  }
                                  aria-sort={
                                    isActive
                                      ? state.direction === "asc"
                                        ? "ascending"
                                        : "descending"
                                      : "none"
                                  }
                                  title={`Sort by ${column.label}`}
                                >
                                  {column.label}
                                  <span className={styles.teamsPageSortIndicator}>
                                    {isActive
                                      ? state.direction === "asc"
                                        ? "▲"
                                        : "▼"
                                      : ""}
                                  </span>
                                </th>
                              );
                            })}
                          </tr>
                        </thead>
                        <tbody>
                          {sortTeams(teams, conference).map((team) => (
                            <tr
                              key={team.id}
                              className={styles.teamsPageTableRow}
                              onClick={() =>
                                navigateToTeam(navigate, team.name)
                              }
                              style={{ cursor: "pointer" }}
                            >
                              <td className={styles.teamsPageTableCellTeam}>
                                <div className={styles.teamsPageTeamInfo}>
                                  <div className={styles.teamsPageTeamLogo}>
                                    <TeamLogo
                                      teamName={team.name}
                                      size="small"
                                    />
                                  </div>
                                  <div className={styles.teamsPageTeamDetails}>
                                    <span
                                      className={styles.teamsPageTeamName}
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        navigateToTeam(navigate, team.name);
                                      }}
                                      style={{ cursor: "pointer" }}
                                    >
                                      {team.name}
                                    </span>
                                    <span
                                      className={styles.teamsPageTeamConference}
                                    >
                                      {formatConferenceName(team.conference)}
                                    </span>
                                  </div>
                                </div>
                              </td>
                              <td className={styles.teamsPageTableCell}>
                                {team.record}
                              </td>
                              <td className={styles.teamsPageTableCell}>
                                {team.stats.conferenceRecord || "-"}
                              </td>
                              <td className={styles.teamsPageTableCell}>
                                {team.stats.pointsPerGame}
                              </td>
                              <td className={styles.teamsPageTableCell}>
                                {team.stats.pointsAllowed}
                              </td>
                              <td className={styles.teamsPageTableCell}>
                                {team.stats.overallPF}
                              </td>
                              <td className={styles.teamsPageTableCell}>
                                {team.stats.overallPA}
                              </td>
                              <td className={styles.teamsPageTableCell}>
                                {team.stats.overallHome || "-"}
                              </td>
                              <td className={styles.teamsPageTableCell}>
                                {team.stats.overallAway || "-"}
                              </td>
                              <td className={styles.teamsPageTableCell}>
                                {team.stats.overallStreak || "-"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ))}
          </section>
        </div>
      </main>
    </div>
  );
};

export default TeamsPage;
