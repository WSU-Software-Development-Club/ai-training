import React from "react";
import "../styles/components/RankingsTable.css";

const RankingsTable = ({ rankings, title = "AP Top 25" }) => {
  if (!rankings || rankings.length === 0) {
    return (
      <div className="rankings-table">
        <h2 className="rankings-table__title">{title}</h2>
        <div className="rankings-table__empty">No rankings data available</div>
      </div>
    );
  }

  return (
    <div className="rankings-table">
      <h2 className="rankings-table__title">{title}</h2>

      <div className="rankings-table__container">
        <table className="rankings-table__table">
          <thead>
            <tr>
              <th className="rankings-table__header">Rank</th>
              <th className="rankings-table__header">School</th>
              <th className="rankings-table__header">Points</th>
              <th className="rankings-table__header">Record</th>
              <th className="rankings-table__header">Previous</th>
            </tr>
          </thead>
          <tbody>
            {rankings.map((team, index) => (
              <tr key={team.rank || index} className="rankings-table__row">
                <td className="rankings-table__cell rankings-table__cell--rank">
                  {team.RANK}
                </td>
                <td className="rankings-table__cell rankings-table__cell--school">
                  {team.SCHOOL}
                </td>
                <td className="rankings-table__cell rankings-table__cell--points">
                  {team.POINTS}
                </td>
                <td className="rankings-table__cell rankings-table__cell--record">
                  {team.RECORD}
                </td>
                <td className="rankings-table__cell rankings-table__cell--previous">
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
