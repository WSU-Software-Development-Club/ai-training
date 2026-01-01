import React from "react";
import { useNavigate } from "react-router-dom";
import styles from "../styles/components/ScoreCard.module.css";
import { navigateToTeam, navigateToComparison } from "../utils/teamNavigation";
import TeamLogo from "./TeamLogo";
import { useTeamBranding } from "../hooks/useTeamBranding";

const ScoreCard = ({ game }) => {
  const navigate = useNavigate();
  const { home, away, game_state, epoch, prediction } = game;

  const homeTeam = home?.names?.short || "Home";
  const awayTeam = away?.names?.short || "Away";

  // Get full team names for navigation (prefer full name, fallback to short)
  const homeTeamFull = home?.names?.full || home?.names?.short || homeTeam;
  const awayTeamFull = away?.names?.full || away?.names?.short || awayTeam;

  // Get actual scores (from game data)
  const homeScore = home?.score ?? null;
  const awayScore = away?.score ?? null;

  // Determine winner (only if game is finished or live and scores are available)
  const isGameFinished = game_state?.isFinished || game_state?.isLive;
  const homeWins =
    isGameFinished &&
    homeScore !== null &&
    awayScore !== null &&
    homeScore > awayScore;
  const awayWins =
    isGameFinished &&
    homeScore !== null &&
    awayScore !== null &&
    awayScore > homeScore;

  // Get predicted scores (from prediction data) and round to nearest integer
  const predictedHomeScore =
    prediction?.home_score != null ? Math.round(prediction.home_score) : null;
  const predictedAwayScore =
    prediction?.away_score != null ? Math.round(prediction.away_score) : null;

  // Determine predicted winner (if predicted scores are available)
  const predictedHomeWins =
    predictedHomeScore !== null &&
    predictedAwayScore !== null &&
    predictedHomeScore > predictedAwayScore;
  const predictedAwayWins =
    predictedHomeScore !== null &&
    predictedAwayScore !== null &&
    predictedAwayScore > predictedHomeScore;

  // Get over/under data
  const predictedTotal = prediction?.predicted_total ?? null;
  const overUnderLine = prediction?.betting_over_under ?? null;
  const overProbability = prediction?.over_probability ?? null;
  const underProbability = prediction?.under_probability ?? null;

  // Calculate actual total if scores are available
  const actualTotal =
    homeScore !== null && awayScore !== null ? homeScore + awayScore : null;

  const conference = home?.conference || away?.conference || "N/A";
  const status = game_state?.isLive
    ? "Live"
    : game_state?.isFinished
    ? "Final"
    : game_state?.isUpcoming
    ? "Upcoming"
    : "Unknown";

  // Get team branding for colors
  const { branding: homeBranding } = useTeamBranding(homeTeamFull);
  const { branding: awayBranding } = useTeamBranding(awayTeamFull);

  // Handle card click to navigate to comparison
  const handleCardClick = (e) => {
    // Don't navigate if clicking on team name (which goes to team page)
    if (e.target.closest(`.${styles.scoreCardTeamName}`)) {
      return;
    }
    navigateToComparison(navigate, awayTeamFull, homeTeamFull);
  };

  // Handle team name click to navigate to team page
  const handleTeamNameClick = (e, teamName) => {
    e.stopPropagation();
    navigateToTeam(navigate, teamName);
  };

  // TODO: this kind of formatting could be done on the backend side to reduce frontend overhead.
  const getFormattedDate = (epoch) => {
    const dateObject = new Date(epoch * 1000);
    return dateObject.toLocaleDateString("en-US", {
      year: "2-digit",
      month: "short",
      day: "numeric",
    });
  };

  const getFormattedTime = (epoch) => {
    const dateObject = new Date(epoch * 1000);
    return dateObject.toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "numeric",
      timeZoneName: "short",
    });
  };

  const getStatusClass = (game_state) => {
    if (game_state.isFinished) return styles.scoreCardStatusFinal;
    if (game_state.isLive) return styles.scoreCardStatusLive;
    if (game_state.isUpcoming) return styles.scoreCardStatusUpcoming;
    return "";
  };

  // Create card style with team colors
  const cardStyle = {
    borderLeft: awayBranding?.primaryColor
      ? `4px solid ${awayBranding.primaryColor}`
      : undefined,
    borderRight: homeBranding?.primaryColor
      ? `4px solid ${homeBranding.primaryColor}`
      : undefined,
  };

  return (
    <div
      className={styles.scoreCard}
      onClick={handleCardClick}
      style={cardStyle}
      title="Click to compare teams"
    >
      <div className={styles.scoreCardHeader}>
        <span className={styles.scoreCardConference}>{conference}</span>
        <span
          className={`${styles.scoreCardStatus} ${getStatusClass(game_state)}`}
        >
          {status}
        </span>
      </div>

      <div className={styles.scoreCardDate}>
        {epoch ? getFormattedDate(epoch) : "TBD"} •{" "}
        {getFormattedTime(epoch) || ""}
      </div>

      <div className={styles.scoreCardTeams}>
        <div className={`${styles.scoreCardTeam} ${styles.scoreCardTeamAway}`}>
          <div className={styles.scoreCardTeamInfo}>
            <div className={styles.scoreCardTeamLogo}>
              <TeamLogo teamName={awayTeamFull} size="medium" />
            </div>
            <div className={styles.scoreCardTeamDetails}>
              <div
                className={`${styles.scoreCardTeamName} ${
                  awayWins ? styles.scoreCardTeamNameWinning : ""
                }`}
                onClick={(e) => handleTeamNameClick(e, awayTeamFull)}
                style={{ cursor: "pointer" }}
                title={`View ${awayTeamFull} team page`}
              >
                {awayTeam}
              </div>
              <div className={styles.scoreCardScoreContainer}>
                <div className={styles.scoreCardScoreGroup}>
                  <div
                    className={`${styles.scoreCardTeamScore} ${
                      awayWins
                        ? styles.scoreCardTeamScoreWinning
                        : homeWins
                        ? styles.scoreCardTeamScoreLosing
                        : ""
                    }`}
                  >
                    {awayScore ?? "-"}
                  </div>
                </div>
                <div className={styles.scoreCardScoreGroup}>
                  <div className={styles.scoreCardScoreLabel}>Predicted</div>
                  <div
                    className={`${styles.scoreCardPredictedScore} ${
                      predictedAwayWins
                        ? styles.scoreCardPredictedScoreWinning
                        : ""
                    }`}
                  >
                    {predictedAwayScore ?? "-"}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className={styles.scoreCardVs}>VS</div>

        <div className={`${styles.scoreCardTeam} ${styles.scoreCardTeamHome}`}>
          <div className={styles.scoreCardTeamInfo}>
            <div className={styles.scoreCardTeamDetails}>
              <div
                className={`${styles.scoreCardTeamName} ${
                  homeWins ? styles.scoreCardTeamNameWinning : ""
                }`}
                onClick={(e) => handleTeamNameClick(e, homeTeamFull)}
                style={{ cursor: "pointer" }}
                title={`View ${homeTeamFull} team page`}
              >
                {homeTeam}
              </div>
              <div className={styles.scoreCardScoreContainer}>
                <div className={styles.scoreCardScoreGroup}>
                  <div
                    className={`${styles.scoreCardTeamScore} ${
                      homeWins
                        ? styles.scoreCardTeamScoreWinning
                        : awayWins
                        ? styles.scoreCardTeamScoreLosing
                        : ""
                    }`}
                  >
                    {homeScore ?? "-"}
                  </div>
                </div>
                <div className={styles.scoreCardScoreGroup}>
                  <div className={styles.scoreCardScoreLabel}>Predicted</div>
                  <div
                    className={`${styles.scoreCardPredictedScore} ${
                      predictedHomeWins
                        ? styles.scoreCardPredictedScoreWinning
                        : ""
                    }`}
                  >
                    {predictedHomeScore ?? "-"}
                  </div>
                </div>
              </div>
            </div>
            <div className={styles.scoreCardTeamLogo}>
              <TeamLogo teamName={homeTeamFull} size="medium" />
            </div>
          </div>
        </div>
      </div>

      {/* Over/Under Section */}
      {overUnderLine !== null &&
        overProbability !== null &&
        underProbability !== null && (
          <div className={styles.scoreCardOverUnder}>
            <div className={styles.scoreCardOverUnderContent}>
              <div className={styles.scoreCardOverUnderItem}>
                <span className={styles.scoreCardOverUnderLabel}>O/U:</span>
                <span className={styles.scoreCardOverUnderValue}>
                  {overUnderLine}
                </span>
              </div>
              <div className={styles.scoreCardOverUnderProb}>
                <span className={styles.scoreCardOverUnderLabel}>O:</span>
                <span
                  className={`${styles.scoreCardOverUnderValue} ${
                    overProbability > 50
                      ? styles.scoreCardOverUnderProbFavored
                      : ""
                  }`}
                >
                  {Math.round(overProbability)}%
                </span>
              </div>
              <div className={styles.scoreCardOverUnderProb}>
                <span className={styles.scoreCardOverUnderLabel}>U:</span>
                <span
                  className={`${styles.scoreCardOverUnderValue} ${
                    underProbability > 50
                      ? styles.scoreCardOverUnderProbFavored
                      : ""
                  }`}
                >
                  {Math.round(underProbability)}%
                </span>
              </div>
            </div>
          </div>
        )}
    </div>
  );
};

export default ScoreCard;
