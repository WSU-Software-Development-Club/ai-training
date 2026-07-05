import React from "react";
import styles from "../styles/components/TeamStatsTable.module.css";

// ESPN-style post-game team-stats comparison. Away sits on the left, home on
// the right (matching the box-score convention), the stat label runs down the
// middle, and the numerically greater side of each row is emphasized. Purely
// presentational — data comes from /matchup/<id>/team-stats.

// Pull the leading number out of a value so "23-43", "6.9", "341" all compare.
const leadNumber = (v) => {
  const m = String(v ?? "").match(/-?\d+(\.\d+)?/);
  return m ? parseFloat(m[0]) : null;
};

const TeamStatsTable = ({ stats }) => {
  const rows = stats?.rows || [];
  if (rows.length === 0) return null;

  const awayAbbrev = stats.away?.abbrev || stats.away?.name || "Away";
  const homeAbbrev = stats.home?.abbrev || stats.home?.name || "Home";

  return (
    <section className={styles.card} aria-label="Team stats">
      <div className={styles.header}>
        <h3 className={styles.title}>Team Stats</h3>
      </div>

      <div className={styles.columns}>
        <span className={`${styles.colTeam} ${styles.colAway}`}>{awayAbbrev}</span>
        <span className={styles.colSpacer} aria-hidden="true" />
        <span className={`${styles.colTeam} ${styles.colHome}`}>{homeAbbrev}</span>
      </div>

      <dl className={styles.rows}>
        {rows.map((row) => {
          const a = leadNumber(row.away);
          const h = leadNumber(row.home);
          const awayLeads = a != null && h != null && a > h;
          const homeLeads = a != null && h != null && h > a;
          return (
            <div key={row.label} className={styles.row}>
              <dd
                className={`${styles.value} ${styles.away} ${
                  awayLeads ? styles.leads : ""
                }`}
              >
                {row.away}
              </dd>
              <dt className={styles.label}>{row.label}</dt>
              <dd
                className={`${styles.value} ${styles.home} ${
                  homeLeads ? styles.leads : ""
                }`}
              >
                {row.home}
              </dd>
            </div>
          );
        })}
      </dl>
    </section>
  );
};

export default TeamStatsTable;
