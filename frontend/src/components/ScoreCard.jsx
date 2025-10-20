import React from "react";
import "../styles/components/ScoreCard.css";

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
        return "score-card__status--final";
      case "live":
        return "score-card__status--live";
      case "upcoming":
        return "score-card__status--upcoming";
      default:
        return "score-card__status--final";
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
    <div className="score-card">
      <div className="score-card__header">
        <span className="score-card__conference">{conference}</span>
        <span className={`score-card__status ${getStatusClass(status)}`}>
          {status}
        </span>
      </div>

      <div className="score-card__date">
        {formatDate(date)} • {time}
      </div>

      <div className="score-card__teams">
        <div className="score-card__team score-card__team--away">
          <div className="score-card__team-name">{awayTeam}</div>
          <div className="score-card__team-score">{awayScore}</div>
        </div>

        <div className="score-card__vs">@</div>

        <div className="score-card__team score-card__team--home">
          <div className="score-card__team-name">{homeTeam}</div>
          <div className="score-card__team-score">{homeScore}</div>
        </div>
      </div>
    </div>
  );
};

export default ScoreCard;
