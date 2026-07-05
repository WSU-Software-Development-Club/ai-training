import React, { useEffect, useState } from "react";
import LoadingSpinner from "./LoadingSpinner";
import PolymarketHistoryChart from "./PolymarketHistoryChart";
import TeamStatsTable from "./TeamStatsTable";
import ScoringSummary from "./ScoringSummary";
import api from "../services/api";
import styles from "../styles/components/PostGamePanel.module.css";

// Post-Game tab. The final score lives in the hero (next to the team titles);
// this tab stacks the game's after-the-fact context:
//   1. the historical Polymarket win-probability chart (when a market existed),
//   2. the ESPN-style team-stats comparison, and
//   3. the quarter-by-quarter scoring summary.
// Each section is fetched independently and only rendered when its data exists
// (a 404 = "not available for this game" → hidden, not an error). If none of
// the three resolve, the tab shows a single empty state.
const PostGamePanel = ({ gameId, matchup }) => {
  const [poly, setPoly] = useState({ status: "loading", data: null });
  const [teamStats, setTeamStats] = useState({ status: "loading", data: null });
  const [scoring, setScoring] = useState({ status: "loading", data: null });

  useEffect(() => {
    if (!gameId) {
      setPoly({ status: "empty", data: null });
      setTeamStats({ status: "empty", data: null });
      setScoring({ status: "empty", data: null });
      return;
    }

    const controller = new AbortController();

    // Each loader resolves to ready|empty; a 404 (no data for this game) or any
    // fetch failure is treated as "empty" so the section is simply hidden.
    const loadInto = (fetcher, setter) => async () => {
      setter({ status: "loading", data: null });
      try {
        const res = await fetcher(gameId, { signal: controller.signal });
        setter({
          status: res && res.success ? "ready" : "empty",
          data: res && res.success ? res.data : null,
        });
      } catch (err) {
        if (err?.name === "AbortError") return;
        setter({ status: "empty", data: null });
      }
    };

    loadInto(api.getMatchupPolymarketHistory, setPoly)();
    loadInto(api.getMatchupTeamStats, setTeamStats)();
    loadInto(api.getMatchupScoringSummary, setScoring)();
    return () => controller.abort();
  }, [gameId]);

  const loading =
    poly.status === "loading" ||
    teamStats.status === "loading" ||
    scoring.status === "loading";

  if (loading) {
    return (
      <div className={styles.state}>
        <LoadingSpinner />
      </div>
    );
  }

  const deck = matchup?.data || {};
  const polyData = poly.data;
  const hasPolyPoints = (polyData?.points?.length || 0) > 0;
  const hasTeamStats = (teamStats.data?.rows?.length || 0) > 0;
  const hasScoring = (scoring.data?.periods?.length || 0) > 0;

  if (!hasPolyPoints && !hasTeamStats && !hasScoring) {
    return (
      <div className={styles.emptyState}>
        No post-game details available for this game yet.
      </div>
    );
  }

  return (
    <div className={styles.postGame}>
      {hasPolyPoints && (
        <PolymarketHistoryChart
          points={polyData.points}
          homeTeam={polyData.home_team || deck.home_team || "Home"}
          awayTeam={polyData.away_team || deck.away_team || "Away"}
          sourceUrl={polyData.source_url}
          kickoff={polyData.kickoff}
        />
      )}
      {hasTeamStats && <TeamStatsTable stats={teamStats.data} />}
      {hasScoring && <ScoringSummary summary={scoring.data} />}
    </div>
  );
};

export default PostGamePanel;
