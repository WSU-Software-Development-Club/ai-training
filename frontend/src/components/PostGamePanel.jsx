import React, { useEffect, useState } from "react";
import LoadingSpinner from "./LoadingSpinner";
import PolymarketHistoryChart from "./PolymarketHistoryChart";
import api from "../services/api";
import styles from "../styles/components/PostGamePanel.module.css";

// Post-Game tab. The final score now lives in the hero (next to the team
// titles), so this tab is the historical Polymarket win-probability chart for
// the game — fetched from /matchup/<id>/polymarket. Most CFB games never had a
// market, in which case the endpoint returns an empty series and this renders
// an empty state.
const PostGamePanel = ({ gameId, matchup }) => {
  const [poly, setPoly] = useState({ status: "loading", data: null });

  useEffect(() => {
    if (!gameId) {
      setPoly({ status: "empty", data: null });
      return;
    }

    const controller = new AbortController();

    const loadPoly = async () => {
      setPoly({ status: "loading", data: null });
      try {
        const res = await api.getMatchupPolymarketHistory(gameId, {
          signal: controller.signal,
        });
        setPoly({
          status: res && res.success ? "ready" : "empty",
          data: res && res.success ? res.data : null,
        });
      } catch (err) {
        if (err?.name === "AbortError") return;
        // A 404 (no game row) — treat as no chart.
        setPoly({ status: "empty", data: null });
      }
    };

    loadPoly();
    return () => controller.abort();
  }, [gameId]);

  if (poly.status === "loading") {
    return (
      <div className={styles.state}>
        <LoadingSpinner />
      </div>
    );
  }

  const deck = matchup?.data || {};
  const polyData = poly.data;
  const hasPolyPoints = (polyData?.points?.length || 0) > 0;

  if (!hasPolyPoints) {
    return (
      <div className={styles.emptyState}>
        No Polymarket market history for this game.
      </div>
    );
  }

  return (
    <div className={styles.postGame}>
      <PolymarketHistoryChart
        points={polyData.points}
        homeTeam={polyData.home_team || deck.home_team || "Home"}
        awayTeam={polyData.away_team || deck.away_team || "Away"}
        sourceUrl={polyData.source_url}
        kickoff={polyData.kickoff}
      />
    </div>
  );
};

export default PostGamePanel;
