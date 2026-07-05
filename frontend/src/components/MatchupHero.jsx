import React from "react";
import TeamLogo from "./TeamLogo";
import { useTeamBranding } from "../hooks/useTeamBranding";
import styles from "../styles/components/MatchupHero.module.css";

// Large matchup container beneath the page title. The away team sits on the
// left and the home team on the right (matching the "AWAY @ HOME" convention),
// with each team's logo faded into the near corner (away top-left, home
// top-right) — the same backdrop treatment as ScoreCard, and team colors
// tinting the matching side border. Everything else for the game (tabs,
// reference panel, the active tab's content) renders inside via `children`,
// below the banner.
const MatchupHero = ({
  homeTeam,
  awayTeam,
  homeScore,
  awayScore,
  statusLabel,
  children,
}) => {
  const { branding: homeBranding } = useTeamBranding(homeTeam);
  const { branding: awayBranding } = useTeamBranding(awayTeam);
  // Show the score block (and the centered status) only once a score exists —
  // an unplayed game keeps the plain home/away banner.
  const hasScore = homeScore != null || awayScore != null;

  // Prefer the dark-mode logo variant for the backdrops (see ScoreCard) so
  // otherwise-dark logos stay visible against the dark surface.
  const homeLogo = homeBranding?.logoDark || homeBranding?.logo;
  const awayLogo = awayBranding?.logoDark || awayBranding?.logo;

  const heroStyle = {
    // Left border tints to the away team (left slot), right border to home.
    borderLeftColor: awayBranding?.primaryColor || "var(--color-secondary)",
    borderRightColor: homeBranding?.primaryColor || "var(--color-secondary)",
    "--home-logo": homeLogo ? `url("${homeLogo}")` : "none",
    "--away-logo": awayLogo ? `url("${awayLogo}")` : "none",
  };

  return (
    <section className={styles.hero} style={heroStyle}>
      <div className={styles.banner}>
        {/* Away team on the LEFT */}
        <div className={`${styles.side} ${styles.left}`}>
          <span className={styles.sideLabel}>Away</span>
          <div className={styles.team}>
            <TeamLogo teamName={awayTeam} size="large" />
            <span className={styles.teamName}>{awayTeam || "Away"}</span>
            {hasScore && <span className={styles.score}>{awayScore ?? "—"}</span>}
          </div>
        </div>

        {hasScore && statusLabel && (
          <span className={styles.status}>{statusLabel}</span>
        )}

        {/* Home team on the RIGHT */}
        <div className={`${styles.side} ${styles.right}`}>
          <span className={styles.sideLabel}>Home</span>
          <div className={styles.team}>
            <TeamLogo teamName={homeTeam} size="large" />
            <span className={styles.teamName}>{homeTeam || "Home"}</span>
            {hasScore && <span className={styles.score}>{homeScore ?? "—"}</span>}
          </div>
        </div>
      </div>

      {children && <div className={styles.body}>{children}</div>}
    </section>
  );
};

export default MatchupHero;
