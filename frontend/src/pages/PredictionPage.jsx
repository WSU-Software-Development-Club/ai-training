import React, { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { FiTarget, FiTrendingUp, FiCheckCircle, FiXCircle } from "react-icons/fi";
import TeamLogo from "../components/TeamLogo";
import LoadingSpinner from "../components/LoadingSpinner";
import api from "../services/api";
import { getCurrentWeek, getCurrentYear } from "../utils/helpers";
import styles from "../styles/pages/PredictionPage.module.css";

const round = (n) => (n != null ? Math.round(n) : null);

// Map a predicted margin to a confidence label + meter fill. The model has a
// score MAE of ~10, so a ~28-point margin is treated as effectively "maxed".
const getConfidence = (margin) => {
  if (margin == null) return { label: "—", pct: 0 };
  const pct = Math.max(8, Math.min(100, Math.round((margin / 28) * 100)));
  let label = "Toss-up";
  if (margin >= 21) label = "High confidence";
  else if (margin >= 10) label = "Solid pick";
  else if (margin >= 4) label = "Lean";
  return { label, pct };
};

// One game's model prediction, rendered as a rich card.
const PredictionCard = ({ game }) => {
  const navigate = useNavigate();
  const { home, away, game_state, epoch, prediction } = game;

  // Only surfaced nested inside the prediction (see scoreboard_service.py) —
  // games without a model prediction have no known NCAA game ID here.
  const ncaaGameId = prediction?.ncaa_game_id ?? null;

  const awayName = away?.names?.short || "Away";
  const homeName = home?.names?.short || "Home";
  const awayFull = away?.names?.full || awayName;
  const homeFull = home?.names?.full || homeName;

  const predAway = round(prediction?.away_score);
  const predHome = round(prediction?.home_score);
  const hasPred = predAway != null && predHome != null;
  const predHomeWins = hasPred && predHome > predAway;
  const predAwayWins = hasPred && predAway > predHome;
  const margin = hasPred ? Math.abs(predHome - predAway) : null;
  const total = hasPred ? predHome + predAway : null;
  const conf = getConfidence(margin);

  const isFinished = game_state?.isFinished;
  const actualAway = away?.score ?? null;
  const actualHome = home?.score ?? null;
  const haveActual = isFinished && actualAway != null && actualHome != null;
  const actualHomeWins = haveActual && actualHome > actualAway;
  const actualAwayWins = haveActual && actualAway > actualHome;
  const correct =
    haveActual && hasPred
      ? (predHomeWins && actualHomeWins) || (predAwayWins && actualAwayWins)
      : null;

  const status = game_state?.isLive
    ? "Live"
    : isFinished
    ? "Final"
    : "Upcoming";
  const statusClass = game_state?.isLive
    ? styles.statusLive
    : isFinished
    ? styles.statusFinal
    : styles.statusUpcoming;

  const ou = prediction?.betting_over_under ?? null;
  const overP = prediction?.over_probability ?? null;
  const underP = prediction?.under_probability ?? null;

  const dateLabel = epoch
    ? new Date(epoch * 1000).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      })
    : "TBD";

  const renderTeam = (name, full, predScore, actualScore, isWinner) => {
    // Only the model's predicted winner is highlighted. Its color reflects the
    // outcome: green when the pick was correct, red when it missed, and the
    // neutral crimson accent while the game hasn't finished yet.
    const highlight = !isWinner
      ? ""
      : correct === true
      ? styles.teamRowHit
      : correct === false
      ? styles.teamRowMiss
      : styles.teamRowWin;

    return (
    <div className={`${styles.teamRow} ${highlight}`}>
      <TeamLogo teamName={full} size="small" />
      <span className={styles.teamName} title={full}>
        {name}
      </span>
      {isWinner && <span className={styles.pickTag}>PICK</span>}
      <div className={styles.teamScores}>
        {haveActual && (
          <span className={styles.actualScore}>{actualScore}</span>
        )}
        <span className={styles.predScore}>{predScore ?? "-"}</span>
      </div>
    </div>
    );
  };

  return (
    <div className={styles.predCard}>
      <div className={styles.predCardTop}>
        <span className={styles.predDate}>{dateLabel}</span>
        <span className={`${styles.statusPill} ${statusClass}`}>{status}</span>
      </div>

      {ncaaGameId && (
        <button
          type="button"
          className={styles.matchupLink}
          onClick={() => navigate(`/matchup/${ncaaGameId}`)}
          aria-label={`View matchup intel for ${awayFull} at ${homeFull}`}
        >
          <FiTarget aria-hidden="true" />
          Matchup intel
        </button>
      )}

      <div className={styles.teams}>
        {renderTeam(awayName, awayFull, predAway, actualAway, predAwayWins)}
        {renderTeam(homeName, homeFull, predHome, actualHome, predHomeWins)}
      </div>

      {hasPred && (
        <>
          <div className={styles.meterHead}>
            <span className={styles.confLabel}>{conf.label}</span>
            <span className={styles.meterMeta}>
              Margin {margin} · Total ~{total}
            </span>
          </div>
          <div className={styles.meterTrack}>
            <div
              className={styles.meterFill}
              style={{ width: `${conf.pct}%` }}
            />
          </div>
        </>
      )}

      <div className={styles.predFooter}>
        {ou != null && overP != null && underP != null && (
          <div className={styles.ouGroup}>
            <span className={styles.ouLabel}>O/U</span>
            <span className={styles.ouValue}>{ou}</span>
            <span className={styles.ouSplit}>
              <span className={overP >= 50 ? styles.ouFavored : ""}>
                O {Math.round(overP)}%
              </span>
              <span className={underP >= 50 ? styles.ouFavored : ""}>
                U {Math.round(underP)}%
              </span>
            </span>
          </div>
        )}

        {correct != null && (
          <span
            className={`${styles.resultBadge} ${
              correct ? styles.resultHit : styles.resultMiss
            }`}
          >
            {correct ? <FiCheckCircle /> : <FiXCircle />}
            {correct ? "Called it" : "Miss"}
          </span>
        )}
      </div>
    </div>
  );
};

const PredictionPage = () => {
  const [week, setWeek] = useState(getCurrentWeek());
  const [year, setYear] = useState(getCurrentYear());
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const controller = new AbortController();

    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await api.getScoreboardByWeek(week, year, {
          signal: controller.signal,
        });
        if (res.success) {
          setGames(res.data?.games ?? []);
        } else {
          setError("No prediction data available for this week.");
        }
      } catch (err) {
        if (err.name === "AbortError") return;
        setError("Unable to load predictions.");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    };

    load();
    return () => controller.abort();
  }, [week, year]);

  // Only games the model actually produced a prediction for.
  const predicted = useMemo(
    () =>
      games.filter(
        (g) => g.prediction?.home_score != null && g.prediction?.away_score != null
      ),
    [games]
  );

  // Summary tiles derived entirely client-side from the week's predictions.
  const summary = useMemo(() => {
    const count = predicted.length;
    const totals = predicted
      .map((g) => Math.round(g.prediction.home_score + g.prediction.away_score))
      .filter((n) => Number.isFinite(n));
    const avgTotal = totals.length
      ? Math.round(totals.reduce((a, b) => a + b, 0) / totals.length)
      : null;

    let graded = 0;
    let hits = 0;
    predicted.forEach((g) => {
      if (!g.game_state?.isFinished) return;
      const aw = g.away?.score;
      const hm = g.home?.score;
      if (aw == null || hm == null) return;
      const pAw = g.prediction.away_score;
      const pHm = g.prediction.home_score;
      graded += 1;
      const predHome = pHm > pAw;
      const actualHome = hm > aw;
      if (predHome === actualHome) hits += 1;
    });

    const accuracy = graded ? Math.round((hits / graded) * 100) : null;
    return { count, avgTotal, graded, hits, accuracy };
  }, [predicted]);

  const weeks = Array.from({ length: 19 }, (_, i) => i + 1);
  const currentYear = new Date().getFullYear();
  const years = Array.from(
    { length: currentYear - 2025 + 1 },
    (_, i) => currentYear - i
  );

  return (
    <div className={styles.predictionPage}>
      <main className={styles.predictionPageMain}>
        <div className={styles.predictionPageContainer}>
          <div className={styles.predictionPageHeader}>
            <h1 className={styles.predictionPageTitle}>Model Predictions</h1>
            <p className={styles.predictionPageSubtitle}>
              XGBoost score predictions for every game — the model's pick,
              projected margin, and over/under read.
            </p>
          </div>

          <div className={styles.filters}>
            <div className={styles.filterGroup}>
              <label className={styles.filterLabel}>Year</label>
              <select
                className={styles.filterSelect}
                value={year}
                onChange={(e) => setYear(Number(e.target.value))}
              >
                {years.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            </div>
            <div className={styles.filterGroup}>
              <label className={styles.filterLabel}>Week</label>
              <select
                className={styles.filterSelect}
                value={week}
                onChange={(e) => setWeek(Number(e.target.value))}
              >
                {weeks.map((w) => (
                  <option key={w} value={w}>
                    Week {w}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {!loading && !error && predicted.length > 0 && (
            <div className={styles.summaryRow}>
              <div className={styles.summaryTile}>
                <FiTarget className={styles.summaryIcon} />
                <span className={styles.summaryValue}>{summary.count}</span>
                <span className={styles.summaryLabel}>Games predicted</span>
              </div>
              {summary.accuracy != null && (
                <div className={styles.summaryTile}>
                  <FiCheckCircle className={styles.summaryIcon} />
                  <span className={styles.summaryValue}>
                    {summary.accuracy}%
                  </span>
                  <span className={styles.summaryLabel}>
                    Winners called ({summary.hits}/{summary.graded})
                  </span>
                </div>
              )}
              {summary.avgTotal != null && (
                <div className={styles.summaryTile}>
                  <FiTrendingUp className={styles.summaryIcon} />
                  <span className={styles.summaryValue}>{summary.avgTotal}</span>
                  <span className={styles.summaryLabel}>Avg projected total</span>
                </div>
              )}
            </div>
          )}

          <section className={styles.predictionPageContent}>
            {loading && (
              <div className={styles.loadingContainer}>
                <LoadingSpinner />
              </div>
            )}

            {!loading && error && (
              <div className={styles.stateBox}>
                <p>{error}</p>
              </div>
            )}

            {!loading && !error && predicted.length === 0 && (
              <div className={styles.stateBox}>
                <FiTarget size={40} className={styles.stateIcon} />
                <p>No model predictions for Week {week}, {year} yet.</p>
                <span className={styles.stateHint}>
                  Predictions are generated weekly — try another week.
                </span>
              </div>
            )}

            {!loading && !error && predicted.length > 0 && (
              <div className={styles.grid}>
                {predicted.map((game) => (
                  <PredictionCard
                    key={`${game.home?.names?.char6}-${game.away?.names?.char6}-${game.epoch}`}
                    game={game}
                  />
                ))}
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
};

export default PredictionPage;
