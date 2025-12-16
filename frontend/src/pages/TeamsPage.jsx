import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Header from "../components/Header";
import { appConfig } from "../constants";
import api from "../services/api";
import styles from "../styles/pages/TeamsPage.module.css";
import LoadingSpinner from "../components/LoadingSpinner";
import TeamLogo from "../components/TeamLogo";
import { navigateToTeam } from "../utils/teamNavigation";

const TeamsPage = () => {
  const navigate = useNavigate();
  const [selectedConference, setSelectedConference] = useState("All");
  const [teams, setTeams] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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

  if (loading) {
    return (
      <div className={styles.teamsPage}>
        <Header title={appConfig.name} onSearch={handleSearch} />
        <main className={styles.teamsPageMain}>
          <div className={styles.loadingContainer}>
            <LoadingSpinner />
          </div>
        </main>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.teamsPage}>
        <Header title={appConfig.name} onSearch={handleSearch} />
        <main className={styles.teamsPageMain}>
          <div className={styles.errorContainer}>
            <p>{error}</p>
          </div>
        </main>
      </div>
    );
  }

  // Extract unique conferences from teams
  const conferenceSet = new Set(
    teams.map((team) => team.conference).filter(Boolean)
  );

  const conferences = [
    { value: "All", label: "All" },
    ...Array.from(conferenceSet)
      .sort()
      .map((conf) => ({
        value: conf,
        label: conf.charAt(0).toUpperCase() + conf.slice(1),
      })),
  ];

  // Filter teams based on selected conference
  const filteredTeams = teams.filter((team) => {
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
            {error && <p className="error">{error}</p>}

            {filteredTeams.length === 0 && (
              <div className={styles.teamsPageNoResults}>
                <p>No teams found matching your filters.</p>
              </div>
            )}

            {filteredTeams.length > 0 &&
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
                      {conference.charAt(0).toUpperCase() + conference.slice(1)}
                    </h2>
                    <div className={styles.teamsPageTableContainer}>
                      <table className={styles.teamsPageTable}>
                        <thead>
                          <tr>
                            <th className={styles.teamsPageTableHeader}>
                              Team
                            </th>
                            <th className={styles.teamsPageTableHeader}>
                              Overall Record
                            </th>
                            <th className={styles.teamsPageTableHeader}>
                              Conf Record
                            </th>
                            <th className={styles.teamsPageTableHeader}>PPG</th>
                            <th className={styles.teamsPageTableHeader}>
                              PAPG
                            </th>
                            <th className={styles.teamsPageTableHeader}>PF</th>
                            <th className={styles.teamsPageTableHeader}>PA</th>
                            <th className={styles.teamsPageTableHeader}>
                              Home
                            </th>
                            <th className={styles.teamsPageTableHeader}>
                              Away
                            </th>
                            <th className={styles.teamsPageTableHeader}>
                              Streak
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {teams.map((team) => (
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
                                      {team.conference}
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
