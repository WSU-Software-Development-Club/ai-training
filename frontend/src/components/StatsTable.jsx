import React from "react";
import styles from "../styles/components/StatsTable.module.css";

const StatsTable = ({ stats, title, statCategory }) => {
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

  // Get the first stat to determine column structure
  const firstStat = stats[0];
  const columns = Object.keys(firstStat).filter(
    (key) => key !== "rank" && key !== "Rank"
  );

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
                  {column.charAt(0).toUpperCase() +
                    column.slice(1).replace(/([A-Z])/g, " $1")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {stats.map((stat, index) => (
              <tr
                key={stat.rank || stat.Rank || index}
                className={styles.statsTableRow}
              >
                <td
                  className={`${styles.statsTableCell} ${styles.statsTableCellRank}`}
                >
                  {stat.rank || stat.Rank}
                </td>
                <td
                  className={`${styles.statsTableCell} ${styles.statsTableCellTeam}`}
                >
                  {stat.team || stat.Team}
                </td>
                {columns.map((column) => (
                  <td key={column} className={styles.statsTableCell}>
                    {stat[column]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default StatsTable;
