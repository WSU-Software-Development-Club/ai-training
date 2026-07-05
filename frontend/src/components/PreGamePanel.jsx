import React from "react";
import styles from "../styles/components/PreGamePanel.module.css";

const round = (n) => (n != null ? Math.round(n) : null);

// Pre-Game tab: leads with our XGBoost score model's prediction for the game as
// the headline pre-game context. Reads the same reference-panel data the
// serving layer assembles (matchup.data.reference_panels.model); the backend
// falls back to building that panel straight from the prediction row when a
// game has no materialized factor deck, so these numbers show for any predicted
// game. Renders an empty state when no model prediction exists yet.
const PreGamePanel = ({ matchup }) => {
  const data = matchup?.data || {};
  const model = data.reference_panels?.model;
  const vegas = data.reference_panels?.vegas;
  const homeTeam = data.home_team || "Home";
  const awayTeam = data.away_team || "Away";

  if (!model) {
    return (
      <div className={styles.empty}>
        <p>No model prediction available for this game yet.</p>
      </div>
    );
  }

  const awayScore = round(model.predicted_away_score);
  const homeScore = round(model.predicted_home_score);
  const winner = model.predicted_winner;
  const margin = round(model.predicted_margin);
  const total = round(model.predicted_total);
  const overUnder = vegas?.over_under ?? null;

  return (
    <div className={styles.preGame}>
      <section className={styles.card}>
        <header className={styles.cardHeader}>
          <span className={styles.badge}>Model Prediction</span>
          <p className={styles.caption}>
            Our XGBoost score model&apos;s projection for this game — a reference
            input, not the factor deck&apos;s verdict.
          </p>
        </header>

        <div className={styles.scoreboard}>
          <div className={styles.side}>
            <span className={styles.sideLabel}>Away</span>
            <span className={styles.teamName}>{awayTeam}</span>
            <span className={styles.score}>{awayScore ?? "–"}</span>
          </div>
          <span className={styles.at} aria-hidden="true">
            @
          </span>
          <div className={styles.side}>
            <span className={styles.sideLabel}>Home</span>
            <span className={styles.teamName}>{homeTeam}</span>
            <span className={styles.score}>{homeScore ?? "–"}</span>
          </div>
        </div>

        <dl className={styles.meta}>
          {winner && (
            <div className={styles.metaItem}>
              <dt>Projected winner</dt>
              <dd className={styles.metaStrong}>{winner}</dd>
            </div>
          )}
          {margin != null && (
            <div className={styles.metaItem}>
              <dt>Margin</dt>
              <dd>{margin}</dd>
            </div>
          )}
          {total != null && (
            <div className={styles.metaItem}>
              <dt>Projected total</dt>
              <dd>{total}</dd>
            </div>
          )}
          {overUnder != null && (
            <div className={styles.metaItem}>
              <dt>Vegas O/U</dt>
              <dd>{overUnder}</dd>
            </div>
          )}
        </dl>
      </section>
    </div>
  );
};

export default PreGamePanel;
