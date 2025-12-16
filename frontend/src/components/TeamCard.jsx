import React from "react";
import { useNavigate } from "react-router-dom";
import styles from "../styles/components/TeamCard.module.css";
import TeamLogo from "./TeamLogo";
import { useTeamBranding } from "../hooks/useTeamBranding";
import { navigateToTeam } from "../utils/teamNavigation";

const TeamCard = ({ team }) => {
  const navigate = useNavigate();
  const { name, conference, record, stats } = team;
  const { branding } = useTeamBranding(name);

  const handleTeamClick = () => {
    navigateToTeam(navigate, name);
  };

  const cardStyle = branding?.primaryColor 
    ? { 
        borderLeftColor: branding.primaryColor,
        borderLeftWidth: '4px',
        borderLeftStyle: 'solid'
      } 
    : {};

  return (
    <div 
      className={styles.teamCard} 
      onClick={handleTeamClick}
      style={cardStyle}
    >
      <div className={styles.teamCardHeader}>
        <div className={styles.teamCardLogo}>
          <TeamLogo teamName={name} size="medium" />
        </div>
        <div className={styles.teamCardInfo}>
          <h3 className={styles.teamCardName}>{name}</h3>
          <span className={styles.teamCardConference}>{conference}</span>
        </div>
      </div>

      <div className={styles.teamCardRecord}>
        <span className={styles.teamCardRecordLabel}>Record:</span>
        <span className={styles.teamCardRecordValue}>{record}</span>
      </div>

      <div className={styles.teamCardStats}>
        <div className={styles.teamCardStat}>
          <span className={styles.teamCardStatLabel}>PPG</span>
          <span className={styles.teamCardStatValue}>
            {stats.pointsPerGame}
          </span>
        </div>
        <div className={styles.teamCardStat}>
          <span className={styles.teamCardStatLabel}>PAPG</span>
          <span className={styles.teamCardStatValue}>
            {stats.pointsAllowed}
          </span>
        </div>
        <div className={styles.teamCardStat}>
          <span className={styles.teamCardStatLabel}>YPG</span>
          <span className={styles.teamCardStatValue}>{stats.totalYards}</span>
        </div>
      </div>
    </div>
  );
};

export default TeamCard;
