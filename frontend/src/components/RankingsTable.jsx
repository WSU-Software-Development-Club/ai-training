import React from "react";
import { useNavigate } from "react-router-dom";
import { navigateToResolvedTeam } from "../utils/teamNavigation";
import styles from "../styles/components/RankingsTable.module.css";

const RankingsTable = ({ rankings, title = "AP Top 25" }) => {
  const navigate = useNavigate();

  const handleTeamClick = (school) => {
    navigateToResolvedTeam(navigate, school);
  };

  if (!rankings || rankings.length === 0) {
    return (
      <div className={styles.rankingsTable}>
        <h2 className={styles.rankingsTableTitle}>{title}</h2>
        <div className={styles.rankingsTableEmpty}>
          No rankings data available
        </div>
      </div>
    );
  }

  return (
    <div className={styles.rankingsTable}>
      <h2 className={styles.rankingsTableTitle}>{title}</h2>

      <div className={styles.rankingsTableContainer}>
        <table className={styles.rankingsTableTable}>
          <thead>
            <tr>
              <th
                className={`${styles.rankingsTableHeader} ${styles.rankingsTableCellRank}`}
              >
                Rank
              </th>
              <th
                className={`${styles.rankingsTableHeader} ${styles.rankingsTableCellTeam}`}
              >
                School
              </th>
              <th
                className={`${styles.rankingsTableHeader} ${styles.rankingsTableCellPoints}`}
              >
                Points
              </th>
              <th
                className={`${styles.rankingsTableHeader} ${styles.rankingsTableCellRecord}`}
              >
                Record
              </th>
              <th
                className={`${styles.rankingsTableHeader} ${styles.rankingsTableCellPrevious}`}
              >
                Previous
              </th>
            </tr>
          </thead>
          <tbody>
            {rankings.map((team, index) => (
              <tr
                key={team.rank || index}
                className={`${styles.rankingsTableRow} ${styles.rankingsTableRowClickable}`}
                onClick={() => handleTeamClick(team.SCHOOL)}
                title={`View ${team.SCHOOL} team page`}
              >
                <td
                  className={`${styles.rankingsTableCell} ${styles.rankingsTableCellRank}`}
                >
                  {team.RANK}
                </td>
                <td
                  className={`${styles.rankingsTableCell} ${styles.rankingsTableCellTeam}`}
                >
                  <span
                    className={styles.rankingsTableTeamLink}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleTeamClick(team.SCHOOL);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        handleTeamClick(team.SCHOOL);
                      }
                    }}
                    role="button"
                    tabIndex={0}
                  >
                    {team.SCHOOL}
                  </span>
                </td>
                <td
                  className={`${styles.rankingsTableCell} ${styles.rankingsTableCellPoints}`}
                >
                  {team.POINTS}
                </td>
                <td
                  className={`${styles.rankingsTableCell} ${styles.rankingsTableCellRecord}`}
                >
                  {team.RECORD}
                </td>
                <td
                  className={`${styles.rankingsTableCell} ${styles.rankingsTableCellPrevious}`}
                >
                  {team.PREVIOUS}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default RankingsTable;
