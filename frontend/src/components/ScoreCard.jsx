import React from "react";
import styles from "../styles/components/ScoreCard.module.css";

const ScoreCard = ({ game }) => {
  const {
    homeTeam,
    awayTeam,
    homeScore,
    awayScore,
    status,
    date,
    time,
    conference,
  } = game;

  const getStatusClass = (status) => {
    switch (status.toLowerCase()) {
      case "final":
        return styles.scoreCardStatusFinal;
      case "live":
        return styles.scoreCardStatusLive;
      case "upcoming":
        return styles.scoreCardStatusUpcoming;
      default:
        return styles.scoreCardStatusFinal;
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });
  };

  return (
    <div className={styles.scoreCard}>
      <div className={styles.scoreCardHeader}>
        <span className={styles.scoreCardConference}>{conference}</span>
        <span className={`${styles.scoreCardStatus} ${getStatusClass(status)}`}>
          {status}
        </span>
      </div>

      <div className={styles.scoreCardDate}>
        {formatDate(date)} • {time}
      </div>

      <div className={styles.scoreCardTeams}>
        <div className={`${styles.scoreCardTeam} ${styles.scoreCardTeamAway}`}>
          <div className={styles.scoreCardTeamName}>{awayTeam}</div>
          <div className={styles.scoreCardTeamScore}>{awayScore}</div>
        </div>

        <div className={styles.scoreCardVs}>@</div>

        <div className={`${styles.scoreCardTeam} ${styles.scoreCardTeamHome}`}>
          <div className={styles.scoreCardTeamName}>{homeTeam}</div>
          <div className={styles.scoreCardTeamScore}>{homeScore}</div>
        </div>
      </div>
    </div>
  );
};

export default ScoreCard;
