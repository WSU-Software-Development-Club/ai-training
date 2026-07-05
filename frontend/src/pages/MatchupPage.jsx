import React, { useEffect, useState } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { FiArrowLeft } from "react-icons/fi";
import GameTabs from "../components/GameTabs";
import MatchupHero from "../components/MatchupHero";
import api from "../services/api";
import styles from "../styles/pages/MatchupPage.module.css";

// Page shell for the matchup view. Owns the single matchup-intel fetch for this
// game, renders the home-vs-away hero from it, and hands the fetched state down
// through the tab switcher — the Post-Game tab (PostGamePanel) renders the
// factor deck; Pre-Game and Live are placeholders for now.
const MatchupPage = () => {
  const { gameId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  // A card for a finished game passes `initialTab: "post"` so we open on the
  // Final tab; direct visits fall back to the default (Pre-Game).
  const initialTab = location.state?.initialTab;
  // status: "loading" | "ready" | "empty" | "error"
  const [state, setState] = useState({ status: "loading", data: null, error: null });
  // Actual score, fetched here (not in the Post-Game tab) so it can render in
  // the hero next to the team titles regardless of the active tab.
  const [score, setScore] = useState(null);

  useEffect(() => {
    if (!gameId) {
      setState({ status: "error", data: null, error: "No game specified." });
      return;
    }

    const controller = new AbortController();

    const load = async () => {
      setState({ status: "loading", data: null, error: null });
      try {
        const res = await api.getMatchup(gameId, { signal: controller.signal });
        if (res && res.success) {
          setState({ status: "ready", data: res.data, error: null });
        } else {
          // success === false without a thrown error (unexpected, but handle
          // it the same as "no deck yet" rather than crashing).
          setState({ status: "empty", data: null, error: null });
        }
      } catch (err) {
        if (err?.name === "AbortError") return;
        const message = err?.message || "";
        // The retry wrapper never retries a 404 (see api.js RETRYABLE_STATUS)
        // and throws before the JSON body — a 404 here just means no factor
        // deck has been assembled for this game yet, which is expected for
        // every game except the seeded ones.
        if (message.includes("404")) {
          setState({ status: "empty", data: null, error: null });
        } else {
          setState({
            status: "error",
            data: null,
            error: "Unable to load matchup intel right now.",
          });
        }
      }
    };

    const loadScore = async () => {
      setScore(null);
      try {
        const res = await api.getMatchupScore(gameId, { signal: controller.signal });
        setScore(res && res.success ? res.data : null);
      } catch (err) {
        if (err?.name === "AbortError") return;
        setScore(null); // 404 / any failure → no score, hero shows plain banner
      }
    };

    load();
    loadScore();
    return () => controller.abort();
  }, [gameId]);

  const data = state.data;
  // Only surface a score in the hero for a played/in-progress game.
  const showScore = score && (score.status === "final" || score.status === "live");
  const statusLabel = score?.status === "live" ? "Live" : "Final";

  return (
    <div className={styles.matchupPage}>
      <main className={styles.matchupPageMain}>
        <div className={styles.matchupPageContainer}>
          <button
            type="button"
            className={styles.backButton}
            onClick={() => navigate(-1)}
          >
            <FiArrowLeft aria-hidden="true" /> Back
          </button>

          <div className={styles.matchupPageHeader}>
            <h1 className={styles.matchupPageTitle}>Matchup Intelligence</h1>
          </div>

          {/* Once the deck is loaded, everything for the game lives inside the
              home-vs-away container: the tab buttons and the active tab's
              content (the Post-Game tab renders its own reference panel + deck).
              Before it's ready (loading/empty/error), the tabs render bare so
              the Post-Game panel can show its own status. Manual switching. */}
          {state.status === "ready" && (data?.home_team || data?.away_team) ? (
            <MatchupHero
              homeTeam={data.home_team}
              awayTeam={data.away_team}
              homeScore={showScore ? score.home_score : null}
              awayScore={showScore ? score.away_score : null}
              statusLabel={showScore ? statusLabel : null}
            >
              <GameTabs gameId={gameId} matchup={state} initialTab={initialTab} />
            </MatchupHero>
          ) : (
            <GameTabs gameId={gameId} matchup={state} initialTab={initialTab} />
          )}
        </div>
      </main>
    </div>
  );
};

export default MatchupPage;
