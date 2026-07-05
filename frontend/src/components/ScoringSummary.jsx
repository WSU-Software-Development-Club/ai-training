import React from "react";
import styles from "../styles/components/ScoringSummary.module.css";

// Post-game scoring feed, grouped by quarter (the narrative "play-by-play").
// Each scoring play shows the team, a description, the game clock, and the
// running score after the play. Data comes from /matchup/<id>/scoring-summary.
const ScoringSummary = ({ summary }) => {
  const periods = summary?.periods || [];
  if (periods.length === 0) return null;

  const awayAbbrev = summary.away?.abbrev || "Away";
  const homeAbbrev = summary.home?.abbrev || "Home";

  return (
    <section className={styles.card} aria-label="Scoring summary">
      <div className={styles.header}>
        <h3 className={styles.title}>Scoring Summary</h3>
        <span className={styles.matchupLabel}>
          {awayAbbrev} <span className={styles.at}>@</span> {homeAbbrev}
        </span>
      </div>

      {periods.map((period, pi) => (
        <div key={`${period.title}-${pi}`} className={styles.period}>
          <div className={styles.periodTitle}>{period.title}</div>
          <ul className={styles.plays}>
            {period.plays.map((play, i) => (
              <li key={i} className={styles.play}>
                <div className={styles.playMain}>
                  <span
                    className={`${styles.badge} ${
                      play.is_home ? styles.badgeHome : styles.badgeAway
                    }`}
                  >
                    {play.team_abbrev || "—"}
                  </span>
                  <div className={styles.playText}>
                    {play.type_label && (
                      <span className={styles.playType}>{play.type_label}</span>
                    )}
                    <span className={styles.playDesc}>{play.text}</span>
                  </div>
                </div>
                <div className={styles.playMeta}>
                  {play.time && <span className={styles.clock}>{play.time}</span>}
                  <span className={styles.runningScore}>
                    <span className={styles.awayScore}>{play.away_score ?? "—"}</span>
                    <span className={styles.scoreDash}>–</span>
                    <span className={styles.homeScore}>{play.home_score ?? "—"}</span>
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      ))}
      <p className={styles.footnote}>
        Score shown as {awayAbbrev}–{homeAbbrev} after each play.
      </p>
    </section>
  );
};

export default ScoringSummary;
