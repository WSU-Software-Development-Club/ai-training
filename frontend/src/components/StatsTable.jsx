import React from "react";
import { useNavigate } from "react-router-dom";
import { navigateToResolvedTeam } from "../utils/teamNavigation";
import styles from "../styles/components/StatsTable.module.css";

const StatsTable = ({ stats, title, statCategory }) => {
  const navigate = useNavigate();

  const handleTeamClick = (teamName) => {
    navigateToResolvedTeam(navigate, teamName);
  };

  if (!stats || stats.length === 0) {
    return (
      <div className={styles.statsTable}>
        <h2 className={styles.statsTableTitle}>{title}</h2>
        <div className={styles.statsTableEmpty}>
          No statistics data available
        </div>
      </div>
    );
  }

  // Get all unique columns from all stats to ensure we capture all data columns
  const allColumns = new Set();
  stats.forEach((stat) => {
    Object.keys(stat).forEach((key) => {
      allColumns.add(key);
    });
  });

  // Filter out Rank and Team columns since they're displayed separately
  const columns = Array.from(allColumns).filter(
    (key) =>
      key !== "rank" && key !== "Rank" && key !== "team" && key !== "Team"
  );

  // Helper function to format column header, handling <br/> tags
  const formatColumnHeader = (columnName) => {
    // Check if column name contains <br/> tags
    if (columnName.includes("<br/>") || columnName.includes("<br>")) {
      // Return JSX with HTML rendering to display line breaks
      return (
        <span
          dangerouslySetInnerHTML={{
            __html: columnName.replace(/<br\s*\/?>/gi, "<br/>"),
          }}
        />
      );
    }
    // Otherwise, display column name as-is from the API
    return columnName;
  };

  return (
    <div className={styles.statsTable}>
      <h2 className={styles.statsTableTitle}>{title}</h2>

      <div className={styles.statsTableContainer}>
        <table className={styles.statsTableTable}>
          <thead>
            <tr>
              <th className={styles.statsTableHeader}>Rank</th>
              <th className={styles.statsTableHeader}>Team</th>
              {columns.map((column) => (
                <th key={column} className={styles.statsTableHeader}>
                  {formatColumnHeader(column)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {stats.map((stat, index) => {
              const teamName = stat.team || stat.Team;
              return (
              <tr
                key={stat.rank || stat.Rank || index}
                className={`${styles.statsTableRow} ${
                  teamName ? styles.statsTableRowClickable : ""
                }`}
                onClick={teamName ? () => handleTeamClick(teamName) : undefined}
                title={teamName ? `View ${teamName} team page` : undefined}
              >
                <td
                  className={`${styles.statsTableCell} ${styles.statsTableCellRank}`}
                >
                  {stat.rank || stat.Rank}
                </td>
                <td
                  className={`${styles.statsTableCell} ${styles.statsTableCellTeam}`}
                >
                  {teamName ? (
                    <span
                      className={styles.statsTableTeamLink}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleTeamClick(teamName);
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          handleTeamClick(teamName);
                        }
                      }}
                      role="button"
                      tabIndex={0}
                    >
                      {teamName}
                    </span>
                  ) : (
                    teamName
                  )}
                </td>
                {columns.map((column) => (
                  <td key={column} className={styles.statsTableCell}>
                    {stat[column]}
                  </td>
                ))}
              </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default StatsTable;
