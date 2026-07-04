import React, { useEffect, useState } from "react";
import LoadingSpinner from "./LoadingSpinner";
import api from "../services/api";
import styles from "../styles/components/PostGamePanel.module.css";

// Post-Game tab — the final score: home score over away score, with a status
// label (Final / Live / Scheduled) beneath.
//
// The score is fetched lazily (this panel only mounts while the Post-Game tab is
// active) from /matchup/<id>/score, which resolves the actual score from the
// NCAA scoreboard. When it can't be resolved (unplayed game, seed id, feed
// down), the scores render as "—".
const PostGamePanel = ({ gameId, matchup }) => {
  const [state, setState] = useState({ status: "loading", data: null });

  useEffect(() => {
    if (!gameId) {
      setState({ status: "empty", data: null });
      return;
    }

    const controller = new AbortController();

    const load = async () => {
      setState({ status: "loading", data: null });
      try {
        const res = await api.getMatchupScore(gameId, { signal: controller.signal });
        setState({
          status: res && res.success ? "ready" : "empty",
          data: res && res.success ? res.data : null,
        });
      } catch (err) {
        if (err?.name === "AbortError") return;
        // A 404 (no game row) or any other failure just means no score to show;
        // the placeholders below still render with the team names we have.
        setState({ status: "empty", data: null });
      }
    };

    load();
    return () => controller.abort();
  }, [gameId]);

  if (state.status === "loading") {
    return (
      <div className={styles.state}>
        <LoadingSpinner />
      </div>
    );
  }

  const score = state.data || {};
  const deck = matchup?.data || {};
  // Team names: prefer the score payload, fall back to the matchup deck.
  const homeTeam = score.home_team || deck.home_team || "Home";
  const awayTeam = score.away_team || deck.away_team || "Away";
  const statusLabel =
    score.status === "live"
      ? "Live"
      : score.status === "pre"
      ? "Scheduled"
      : "Final";

  return (
    <div className={styles.finalScore}>
      <div className={`${styles.scoreSide} ${styles.home}`}>
        <span className={styles.teamName}>{homeTeam}</span>
        <span className={styles.score}>{score.home_score ?? "—"}</span>
      </div>
      <span className={styles.finalLabel}>{statusLabel}</span>
      <div className={`${styles.scoreSide} ${styles.away}`}>
        <span className={styles.teamName}>{awayTeam}</span>
        <span className={styles.score}>{score.away_score ?? "—"}</span>
      </div>
    </div>
  );
};

export default PostGamePanel;
