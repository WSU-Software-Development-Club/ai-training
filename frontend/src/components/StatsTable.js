import React from "react";
import "../styles/components/StatsTable.css";

const StatsTable = ({ stats, title, statCategory }) => {
  if (!stats || stats.length === 0) {
    return (
      <div className="stats-table">
        <h2 className="stats-table__title">{title}</h2>
        <div className="stats-table__empty">No statistics data available</div>
      </div>
    );
  }

  // Get the first stat to determine column structure
  const firstStat = stats[0];
  const columns = Object.keys(firstStat).filter((key) => key !== "rank");

  return (
    <div className="stats-table">
      <h2 className="stats-table__title">{title}</h2>

      <div className="stats-table__container">
        <table className="stats-table__table">
          <thead>
            <tr>
              <th className="stats-table__header">Rank</th>
              <th className="stats-table__header">Team</th>
              {columns.map((column) => (
                <th key={column} className="stats-table__header">
                  {column.charAt(0).toUpperCase() +
                    column.slice(1).replace(/([A-Z])/g, " $1")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {stats.map((stat, index) => (
              <tr key={stat.rank || index} className="stats-table__row">
                <td className="stats-table__cell stats-table__cell--rank">
                  {stat.rank}
                </td>
                <td className="stats-table__cell stats-table__cell--team">
                  {stat.team}
                </td>
                {columns.map((column) => (
                  <td key={column} className="stats-table__cell">
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
