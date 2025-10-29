import React from "react";
import styles from "../styles/components/RankingsTable.module.css";

const RankingsTable = ({ rankings, title = "AP Top 25" }) => {
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
              <th className={styles.rankingsTableHeader}>Rank</th>
              <th className={styles.rankingsTableHeader}>School</th>
              <th className={styles.rankingsTableHeader}>Points</th>
              <th className={styles.rankingsTableHeader}>Record</th>
              <th className={styles.rankingsTableHeader}>Previous</th>
            </tr>
          </thead>
          <tbody>
            {rankings.map((team, index) => (
              <tr key={team.rank || index} className={styles.rankingsTableRow}>
                <td
                  className={`${styles.rankingsTableCell} ${styles.rankingsTableCellRank}`}
                >
                  {team.RANK}
                </td>
                <td
                  className={`${styles.rankingsTableCell} ${styles.rankingsTableCellTeam}`}
                >
                  {team.SCHOOL}
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
                <td className={styles.rankingsTableCell}>{team.PREVIOUS}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default RankingsTable;
