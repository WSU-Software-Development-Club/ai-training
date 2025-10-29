import React from "react";
import styles from "../styles/components/TeamCard.module.css";

const TeamCard = ({ team }) => {
  const { name, conference, record, stats } = team;

  const handleTeamClick = () => {
    // TODO: Navigate to team detail page
    console.log(`Navigate to ${name} team page`);
  };

  return (
    <div className={styles.teamCard} onClick={handleTeamClick}>
      <div className={styles.teamCardHeader}>
        <div className={styles.teamCardLogo}>
          {/* Placeholder for team logo */}
          <div className={styles.teamCardLogoPlaceholder}>{name.charAt(0)}</div>
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
