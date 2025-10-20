import React from "react";
import "../styles/components/TeamCard.css";

const TeamCard = ({ team }) => {
  const { name, conference, record, stats } = team;

  const handleTeamClick = () => {
    // TODO: Navigate to team detail page
    console.log(`Navigate to ${name} team page`);
  };

  return (
    <div className="team-card" onClick={handleTeamClick}>
      <div className="team-card__header">
        <div className="team-card__logo">
          {/* Placeholder for team logo */}
          <div className="team-card__logo-placeholder">{name.charAt(0)}</div>
        </div>
        <div className="team-card__info">
          <h3 className="team-card__name">{name}</h3>
          <span className="team-card__conference">{conference}</span>
        </div>
      </div>

      <div className="team-card__record">
        <span className="team-card__record-label">Record:</span>
        <span className="team-card__record-value">{record}</span>
      </div>

      <div className="team-card__stats">
        <div className="team-card__stat">
          <span className="team-card__stat-label">PPG</span>
          <span className="team-card__stat-value">{stats.pointsPerGame}</span>
        </div>
        <div className="team-card__stat">
          <span className="team-card__stat-label">PAPG</span>
          <span className="team-card__stat-value">{stats.pointsAllowed}</span>
        </div>
        <div className="team-card__stat">
          <span className="team-card__stat-label">YPG</span>
          <span className="team-card__stat-value">{stats.totalYards}</span>
        </div>
      </div>
    </div>
  );
};

export default TeamCard;
