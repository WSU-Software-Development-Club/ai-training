import React from "react";
import styles from "../styles/components/ScoreCard.module.css";


const ScoreCard = ({ game }) => {
  const {
    home,
    away,
    game_state,
    epoch
  } = game;

  const homeTeam = home?.names?.short || "Home";
  const awayTeam = away?.names?.short || "Away";
  const homeScore = home?.score ?? "-";
  const awayScore = away?.score ?? "-";
  const conference = home?.conference || away?.conference || "N/A";
  const status = game_state?.isLive
    ? "Live"
    : game_state?.isFinished
    ? "Final"
    : game_state?.isUpcoming
    ? "Upcoming"
    : "Unknown";

  // TODO: this kind of formatting could be done on the backend side to reduce frontend overhead.
  const getFormattedDate = (epoch) => {
    const dateObject = new Date(epoch*1000);
    return dateObject.toLocaleDateString('en-US', {
      year: '2-digit',
      month: 'short',
      day: 'numeric',
    });
  };

  const getFormattedTime = (epoch) => {
    const dateObject = new Date(epoch*1000);
    return dateObject.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: 'numeric',
      timeZoneName: 'short',
    })
  }
  
  const getStatusClass = (game_state) => {
    if (game_state.isFinished) return styles.scoreCardStatusFinal;
    if (game_state.isLive) return styles.scoreCardStatusLive;
    if (game_state.isUpcoming) return styles.scoreCardStatusUpcoming;
    return "";
  }

  return (
    <div className={styles.scoreCard}>
      <div className={styles.scoreCardHeader}>
        <span className={styles.scoreCardConference}>{conference}</span>
        <span className={`${styles.scoreCardStatus} ${getStatusClass(game_state)}`}>
          {status}
        </span>
      </div>

      <div className={styles.scoreCardDate}>
        {epoch ? getFormattedDate(epoch) : "TBD"} • {getFormattedTime(epoch) || ""}
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
