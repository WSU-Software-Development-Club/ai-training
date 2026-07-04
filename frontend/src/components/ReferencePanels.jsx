import React from "react";
import styles from "../styles/pages/MatchupPage.module.css";

const round = (n) => (n != null ? Math.round(n) : null);

// Layer-6 reference panel: model/vegas/polymarket, explicitly framed as
// context inputs rather than the deck's own verdict. Rendered at the top of the
// matchup container (below the tab buttons) as game-level context.
const ReferencePanels = ({ panels }) => {
  const model = panels?.model;
  const vegas = panels?.vegas;
  const polymarket = panels?.polymarket;

  return (
    <section className={styles.referenceSection}>
      <h2 className={styles.referenceTitle}>For reference — inputs, not the verdict</h2>
      <p className={styles.referenceSubtitle}>
        These come from separate systems (the score model, betting markets) and
        are not used to score the factor deck below — shown here purely as
        outside context.
      </p>

      {!panels ? (
        <p className={styles.referenceEmpty}>
          No reference predictions available for this game yet.
        </p>
      ) : (
        <div className={styles.referenceGrid}>
          <div className={styles.referenceCard}>
            <span className={styles.referenceCardLabel}>Model prediction</span>
            {model ? (
              <>
                <div className={styles.referenceScoreRow}>
                  <span className={styles.referenceScore}>
                    {round(model.predicted_away_score) ?? "–"}
                  </span>
                  <span className={styles.referenceVs}>@</span>
                  <span className={styles.referenceScore}>
                    {round(model.predicted_home_score) ?? "–"}
                  </span>
                </div>
                <div className={styles.referenceDetail}>
                  {model.predicted_winner && <span>Pick: {model.predicted_winner}</span>}
                  {model.predicted_margin != null && (
                    <span>Margin {round(model.predicted_margin)}</span>
                  )}
                  {model.predicted_total != null && (
                    <span>Total ~{round(model.predicted_total)}</span>
                  )}
                </div>
              </>
            ) : (
              <span className={styles.referenceNA}>Not available</span>
            )}
          </div>

          <div className={styles.referenceCard}>
            <span className={styles.referenceCardLabel}>Vegas</span>
            {vegas && vegas.over_under != null ? (
              <div className={styles.referenceScoreRow}>
                <span className={styles.referenceScore}>{vegas.over_under}</span>
                <span className={styles.referenceDetail}>Over/Under</span>
              </div>
            ) : (
              <span className={styles.referenceNA}>Not available</span>
            )}
          </div>

          <div className={styles.referenceCard}>
            <span className={styles.referenceCardLabel}>Polymarket</span>
            {polymarket ? (
              <pre className={styles.referenceRaw}>{JSON.stringify(polymarket)}</pre>
            ) : (
              <span className={styles.referenceNA}>Not available</span>
            )}
          </div>
        </div>
      )}
    </section>
  );
};

export default ReferencePanels;
