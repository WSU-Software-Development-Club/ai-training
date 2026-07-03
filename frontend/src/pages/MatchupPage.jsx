import React, { useEffect, useId, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  FiArrowLeft,
  FiChevronDown,
  FiExternalLink,
  FiTrendingUp,
  FiTrendingDown,
  FiMinus,
  FiTarget,
  FiBarChart2,
  FiInfo,
} from "react-icons/fi";
import TeamLogo from "../components/TeamLogo";
import LoadingSpinner from "../components/LoadingSpinner";
import api from "../services/api";
import styles from "../styles/pages/MatchupPage.module.css";

const round = (n) => (n != null ? Math.round(n) : null);
const pct = (n) => (n != null ? `${Math.round(n * 100)}%` : null);

const DIRECTION_META = {
  tailwind: { label: "Tailwind", icon: FiTrendingUp, cls: "tailwind" },
  headwind: { label: "Headwind", icon: FiTrendingDown, cls: "headwind" },
  neutral: { label: "Neutral", icon: FiMinus, cls: "neutral" },
};

const SCORING_METHOD_LABEL = {
  llm: "LLM-scored",
  model: "Model-scored",
  hybrid: "Hybrid-scored",
};

const formatTimestamp = (ts) => {
  if (!ts) return null;
  const date = new Date(ts);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  });
};

// Group a team's factors by category. Categories are ordered by their
// highest-scoring factor, and factors within a category are ranked by
// score (magnitude x confidence) descending — matches the backend's own
// `rank_factors` ordering.
const groupByCategory = (factors) => {
  const sorted = [...factors].sort((a, b) => (b.score ?? 0) - (a.score ?? 0));
  const groups = new Map();
  sorted.forEach((factor) => {
    const key = factor.category || "Other";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(factor);
  });
  return Array.from(groups.entries());
};

// One expandable tailwind/headwind factor card. The whole head is a <button>
// so it's keyboard-operable (Enter/Space) for free, with aria-expanded/
// aria-controls wiring the disclosure semantics.
const FactorCard = ({ factor }) => {
  const [expanded, setExpanded] = useState(false);
  const panelId = useId();
  const dir = DIRECTION_META[factor.direction] || DIRECTION_META.neutral;
  const Icon = dir.icon;
  const magnitudePct = Math.round((factor.magnitude ?? 0) * 100);
  const confidencePct = pct(factor.confidence);
  const explanation = factor.explanation || "No explanation provided.";
  const withheld = factor.historical_rate_withheld || factor.historical_rate == null;
  const sources = factor.sources || [];

  return (
    <div className={`${styles.factorCard} ${styles[dir.cls]}`}>
      <button
        type="button"
        className={styles.factorCardHead}
        onClick={() => setExpanded((e) => !e)}
        aria-expanded={expanded}
        aria-controls={panelId}
      >
        <span className={`${styles.directionBadge} ${styles[dir.cls]}`}>
          <Icon aria-hidden="true" />
          {dir.label}
        </span>
        <span className={styles.factorCategory}>{factor.category}</span>
        <span className={styles.factorSummary} title={explanation}>
          {explanation}
        </span>
        <FiChevronDown
          className={`${styles.chevron} ${expanded ? styles.chevronOpen : ""}`}
          aria-hidden="true"
        />
      </button>

      <div className={styles.meterRow}>
        <div
          className={styles.meterTrack}
          role="img"
          aria-label={`Magnitude ${magnitudePct}%`}
        >
          <div
            className={`${styles.meterFill} ${styles[dir.cls]}`}
            style={{ width: `${magnitudePct}%` }}
          />
        </div>
        <span className={styles.meterValue}>{magnitudePct}%</span>
      </div>

      {expanded && (
        <div id={panelId} className={styles.factorDetails}>
          <p className={styles.factorExplanation}>{explanation}</p>

          <dl className={styles.factorMeta}>
            {confidencePct != null && (
              <div className={styles.metaItem}>
                <dt>Confidence</dt>
                <dd>{confidencePct}</dd>
              </div>
            )}
            <div className={styles.metaItem}>
              <dt>Historical grounding</dt>
              <dd>
                {withheld
                  ? `Insufficient history (n=${factor.sample_size ?? 0})`
                  : `${pct(factor.historical_rate)} historical hit rate (n=${factor.sample_size})`}
              </dd>
            </div>
            {factor.scoring_method && (
              <div className={styles.metaItem}>
                <dt>Scoring method</dt>
                <dd className={styles.scoringMethod}>
                  {SCORING_METHOD_LABEL[factor.scoring_method] || factor.scoring_method}
                </dd>
              </div>
            )}
          </dl>

          {factor.raw_signal && (
            <p className={styles.rawSignal}>
              <FiInfo aria-hidden="true" />
              {factor.raw_signal}
            </p>
          )}

          {sources.length > 0 && (
            <div className={styles.sources}>
              <span className={styles.sourcesLabel}>Sources</span>
              <ul className={styles.sourcesList}>
                {sources.map((src, i) => (
                  <li key={src.url || `${src.source_type}-${i}`} className={styles.sourceItem}>
                    {src.url ? (
                      <a
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={styles.sourceLink}
                      >
                        {src.source_type || "source"}
                        <FiExternalLink aria-hidden="true" />
                      </a>
                    ) : (
                      <span className={styles.sourceType}>{src.source_type || "source"}</span>
                    )}
                    {src.snippet && (
                      <p className={styles.sourceSnippet}>&ldquo;{src.snippet}&rdquo;</p>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// One team's full ranked, categorized factor deck.
const TeamFactorDeck = ({ team }) => {
  const grouped = useMemo(() => groupByCategory(team.factors || []), [team.factors]);
  const asOf = formatTimestamp(team.as_of_timestamp);

  return (
    <div className={styles.teamColumn}>
      <div className={styles.teamColumnHeader}>
        <TeamLogo teamName={team.team_name} size="medium" />
        <div className={styles.teamColumnHeaderText}>
          <h2 className={styles.teamColumnName}>{team.team_name || "Unknown team"}</h2>
          {asOf && <span className={styles.asOf}>As of {asOf}</span>}
        </div>
      </div>

      {grouped.length === 0 && (
        <p className={styles.noFactors}>No factors scored for this team yet.</p>
      )}

      {grouped.map(([category, factors]) => (
        <section key={category} className={styles.categoryGroup}>
          <h3 className={styles.categoryHeading}>{category}</h3>
          <div className={styles.factorList}>
            {factors.map((factor, i) => (
              <FactorCard key={`${category}-${i}`} factor={factor} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
};

// Layer-6 reference panel: model/vegas/polymarket, explicitly framed as
// context inputs rather than the deck's own verdict.
const ReferencePanels = ({ panels }) => {
  const model = panels?.model;
  const vegas = panels?.vegas;
  const polymarket = panels?.polymarket;

  return (
    <section className={styles.referenceSection}>
      <h2 className={styles.referenceTitle}>For reference — inputs, not the verdict</h2>
      <p className={styles.referenceSubtitle}>
        These come from separate systems (the score model, betting markets) and
        are not used to score the factor deck above — shown here purely as
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

const MatchupPage = () => {
  const { gameId } = useParams();
  const navigate = useNavigate();
  // status: "loading" | "ready" | "empty" | "error"
  const [state, setState] = useState({ status: "loading", data: null, error: null });

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

    load();
    return () => controller.abort();
  }, [gameId]);

  const teams = state.data?.teams || [];

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
            <p className={styles.matchupPageSubtitle}>
              Factor-by-factor tailwinds and headwinds for this game, ranked by
              impact, with every claim traceable back to a source.
            </p>
          </div>

          {state.status === "loading" && (
            <div className={styles.loadingContainer}>
              <LoadingSpinner />
            </div>
          )}

          {state.status === "error" && (
            <div className={styles.stateBox}>
              <FiBarChart2 size={40} className={styles.stateIcon} aria-hidden="true" />
              <p>{state.error}</p>
            </div>
          )}

          {state.status === "empty" && (
            <div className={styles.stateBox}>
              <FiTarget size={40} className={styles.stateIcon} aria-hidden="true" />
              <p>No matchup intel for this game yet.</p>
              <span className={styles.stateHint}>
                The Matchup Intelligence Engine is still rolling out — check
                back once a factor deck has been assembled for this game.
              </span>
            </div>
          )}

          {state.status === "ready" && (
            <>
              <ReferencePanels panels={state.data.reference_panels} />

              {teams.length === 0 ? (
                <div className={styles.stateBox}>
                  <p>No team factor decks found for this game.</p>
                </div>
              ) : (
                <div className={styles.teamsGrid}>
                  {teams.map((team) => (
                    <TeamFactorDeck key={team.team_id} team={team} />
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
};

export default MatchupPage;
