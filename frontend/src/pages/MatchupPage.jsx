import React, { useEffect, useId, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  FiArrowLeft,
  FiChevronDown,
  FiSun,
  FiCloudRain,
  FiCloudSnow,
  FiWind,
  FiCloud,
  FiTarget,
  FiBarChart2,
  FiTrendingUp,
  FiTrendingDown,
  FiActivity,
  FiAlertCircle,
  FiClock,
  FiMapPin,
  FiZap,
  FiUsers,
  FiStar,
  FiFileText,
  FiShield,
  FiExternalLink,
} from "react-icons/fi";
import TeamLogo from "../components/TeamLogo";
import LoadingSpinner from "../components/LoadingSpinner";
import api from "../services/api";
import styles from "../styles/pages/MatchupPage.module.css";

const round = (n) => (n != null ? Math.round(n) : null);
const pct = (n) => (n != null ? `${Math.round(n * 100)}%` : null);

// Weather-bucket -> glyph. Falls back to a generic cloud for anything unmapped.
const BUCKET_ICON = {
  cold: FiCloudSnow,
  rain: FiCloudRain,
  heat: FiSun,
  wind: FiWind,
  clear: FiSun,
};

const BUCKET_LABEL = {
  cold: "Freezing conditions",
  rain: "Rain likely",
  heat: "Extreme heat",
  wind: "High wind",
  clear: "Clear conditions",
};

// Deviation (percentage points) of a rate vs. a baseline — the headline signal.
const ppDelta = (rate, baseline) =>
  rate != null && baseline != null ? Math.round((rate - baseline) * 100) : null;

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

// Rank factors within a group by score (magnitude x confidence) descending —
// matches the backend's own `rank_factors` ordering.
const byScore = (factors) =>
  [...factors].sort((a, b) => (b.score ?? 0) - (a.score ?? 0));

// Category -> label + glyph for a team-specific (non-weather) factor. Weather
// has its own dedicated row, so it isn't in here.
const CATEGORY_META = {
  QB: { label: "Quarterback", Icon: FiActivity },
  injury: { label: "Injury", Icon: FiAlertCircle },
  OL: { label: "O-line", Icon: FiShield },
  DL: { label: "D-line", Icon: FiShield },
  rest: { label: "Rest", Icon: FiClock },
  travel: { label: "Travel", Icon: FiMapPin },
  momentum: { label: "Momentum", Icon: FiZap },
  coaching: { label: "Coaching", Icon: FiUsers },
  special_teams: { label: "Special teams", Icon: FiStar },
  discipline: { label: "Discipline", Icon: FiAlertCircle },
  news: { label: "News", Icon: FiFileText },
};

const categoryMeta = (category) =>
  CATEGORY_META[category] || {
    label: category ? category.replace(/_/g, " ") : "Factor",
    Icon: FiTarget,
  };

// Coarse relative time ("3h ago", "2d ago") — the news-timing signal a sharp
// reader scans for: how fresh is this, did it land before the line moved.
const relTime = (ts) => {
  if (!ts) return null;
  const then = new Date(ts).getTime();
  if (Number.isNaN(then)) return null;
  const mins = Math.round((Date.now() - then) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.round(hrs / 24);
  return `${days}d ago`;
};

// A team-specific factor: a direction badge + category + one-line summary, a
// magnitude meter, and — on expand — the full read, confidence/method, and the
// sourced signals (with when each was published) it was built from.
const FactorCard = ({ factor }) => {
  const [expanded, setExpanded] = useState(false);
  const panelId = useId();
  const dir = factor.direction || "neutral";
  const { label, Icon } = categoryMeta(factor.category);
  const magnitude = factor.magnitude != null ? Math.round(factor.magnitude * 100) : null;
  const sources = factor.sources || [];
  const TrendIcon = dir === "headwind" ? FiTrendingDown : FiTrendingUp;

  return (
    <div className={`${styles.factorCard} ${styles[dir]}`}>
      <button
        type="button"
        className={styles.factorCardHead}
        onClick={() => setExpanded((e) => !e)}
        aria-expanded={expanded}
        aria-controls={panelId}
      >
        <span className={`${styles.directionBadge} ${styles[dir]}`}>
          {dir !== "neutral" && <TrendIcon aria-hidden="true" />}
          {dir === "headwind" ? "Headwind" : dir === "tailwind" ? "Tailwind" : "Neutral"}
        </span>
        <span className={styles.factorCategory}>
          <Icon aria-hidden="true" /> {label}
        </span>
        <span className={styles.factorSummary}>{factor.explanation}</span>
        <FiChevronDown
          className={`${styles.chevron} ${expanded ? styles.chevronOpen : ""}`}
          aria-hidden="true"
        />
      </button>

      {magnitude != null && (
        <div className={styles.meterRow}>
          <span className={styles.meterTrack}>
            <span
              className={`${styles.meterFill} ${styles[dir]}`}
              style={{ width: `${magnitude}%` }}
            />
          </span>
          <span className={styles.meterValue}>{magnitude}</span>
        </div>
      )}

      {expanded && (
        <div id={panelId} className={styles.factorDetails}>
          <p className={styles.factorExplanation}>{factor.explanation}</p>

          <dl className={styles.factorMeta}>
            <div className={styles.metaItem}>
              <dt>Impact</dt>
              <dd>{magnitude != null ? `${magnitude}/100` : "—"}</dd>
            </div>
            <div className={styles.metaItem}>
              <dt>Confidence</dt>
              <dd>{pct(factor.confidence) ?? "—"}</dd>
            </div>
            {factor.scoring_method && (
              <div className={styles.metaItem}>
                <dt>Method</dt>
                <dd className={styles.scoringMethod}>{factor.scoring_method}</dd>
              </div>
            )}
          </dl>

          {sources.length > 0 && (
            <div className={styles.sources}>
              <span className={styles.sourcesLabel}>Sources</span>
              <ul className={styles.sourcesList}>
                {sources.map((s, i) => {
                  const when = relTime(s.published_at);
                  return (
                    <li key={i} className={styles.sourceItem}>
                      {s.url ? (
                        <a
                          className={styles.sourceLink}
                          href={s.url}
                          target="_blank"
                          rel="noreferrer noopener"
                        >
                          <FiExternalLink aria-hidden="true" />
                          {s.source_type || "source"}
                          {when && ` · ${when}`}
                        </a>
                      ) : (
                        <span className={styles.sourceType}>
                          {s.source_type || "source"}
                          {when && ` · ${when}`}
                        </span>
                      )}
                      {s.snippet && <p className={styles.sourceSnippet}>“{s.snippet}”</p>}
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// One side of the shared weather row: this team's deviation (headline), its
// raw rate/record with always-on n, and the market line right next to it so a
// reader can reconcile "historically strong in rain" against "already favored".
const WeatherSide = ({ label, teamName, factor, betting }) => {
  if (!factor) {
    return (
      <div className={styles.wxSide}>
        <div className={styles.wxSideTeam}>
          <span className={styles.wxSideLabel}>{label}</span>
        </div>
        <span className={styles.wxSideEmpty}>No weather signal for this team.</span>
      </div>
    );
  }

  const g = factor.grounding || {};
  const total = g.total ?? factor.sample_size;
  const wins = g.wins;
  const losses = wins != null && total != null ? total - wins : null;
  // Prefer the guarded headline rate; fall back to the raw record so a thin
  // sample still shows its number (muted) rather than a "hidden" contradiction.
  const rate =
    factor.historical_rate != null
      ? factor.historical_rate
      : total
      ? wins / total
      : null;
  const baseline = g.baseline;
  const delta = ppDelta(rate, baseline);
  const thin = factor.historical_rate_withheld || (total != null && total < 30);
  const tone = delta == null ? "" : delta >= 0 ? styles.up : styles.down;
  const spread = betting?.spread;
  const ou = betting?.over_under;
  const marketLabel =
    spread == null
      ? null
      : spread > 0
      ? `Fav ${spread}`
      : spread < 0
      ? `Dog ${Math.abs(spread)}`
      : "Pick 'em";

  return (
    <div className={styles.wxSide}>
      <div className={styles.wxSideTeam}>
        <TeamLogo teamName={teamName} size="small" />
        <span className={styles.wxSideLabel}>{label}</span>
      </div>

      {delta != null ? (
        <div className={`${styles.wxSideDelta} ${tone}`}>
          {delta >= 0 ? (
            <FiTrendingUp aria-hidden="true" />
          ) : (
            <FiTrendingDown aria-hidden="true" />
          )}
          {delta > 0 ? `+${delta}` : delta}
          <span className={styles.wxSideDeltaUnit}>pp vs. baseline</span>
        </div>
      ) : (
        <span className={styles.wxSideDeltaNa}>No baseline yet</span>
      )}

      <div className={`${styles.wxSideStat} ${thin ? styles.thin : ""}`}>
        <span className={styles.wxSideRate}>{rate != null ? pct(rate) : "—"}</span>
        {wins != null && losses != null && (
          <span className={styles.wxSideRecord}>
            ({wins}&ndash;{losses})
          </span>
        )}
        <span className={styles.wxSideN}>n={total ?? 0}</span>
        {thin && (
          <span
            className={styles.wxThinFlag}
            title="Below the significance threshold — treat as noise-prone"
          >
            thin
          </span>
        )}
      </div>

      {baseline != null && (
        <span className={styles.wxSideBaseline}>
          baseline (all weather) {pct(baseline)}
        </span>
      )}

      {(spread != null || ou != null) && (
        <div className={styles.wxSideMarket}>
          <FiBarChart2 aria-hidden="true" className={styles.wxSideMarketIcon} />
          {marketLabel && <span>{marketLabel}</span>}
          {ou != null && <span>O/U {ou}</span>}
        </div>
      )}
    </div>
  );
};

// Shared weather row for the whole matchup — one condition, both teams' history
// side by side. Weather is a tiebreaker, not a thesis, so it stays one compact
// band above the team columns rather than a hero card.
const WeatherRow = ({ away, home }) => {
  const [expanded, setExpanded] = useState(false);
  const panelId = useId();
  const factor = away?.factor || home?.factor;
  if (!factor) return null;

  const g = factor.grounding || {};
  const bucket = g.condition_bucket;
  const Icon = BUCKET_ICON[bucket] || FiCloud;
  const precipProb = g.conditions?.precip_prob;
  const forecastKnown = g.is_forecast != null;

  return (
    <section className={styles.wxRow}>
      <button
        type="button"
        className={styles.wxRowHead}
        onClick={() => setExpanded((e) => !e)}
        aria-expanded={expanded}
        aria-controls={panelId}
      >
        <span className={styles.wxRowIcon}>
          <Icon aria-hidden="true" />
        </span>
        <span className={styles.wxRowLabel}>{BUCKET_LABEL[bucket] || "Weather"}</span>
        {precipProb != null && (
          <span className={styles.wxRowProb}>{pct(precipProb)} chance</span>
        )}
        {forecastKnown && (
          <span className={styles.wxRowTag}>{g.is_forecast ? "Forecast" : "Observed"}</span>
        )}
        <FiChevronDown
          className={`${styles.chevron} ${expanded ? styles.chevronOpen : ""}`}
          aria-hidden="true"
        />
      </button>

      <div className={styles.wxRowBody}>
        <WeatherSide
          label="Away"
          teamName={away?.teamName}
          factor={away?.factor}
          betting={away?.betting}
        />
        <span className={styles.wxRowDivider} aria-hidden="true" />
        <WeatherSide
          label="Home"
          teamName={home?.teamName}
          factor={home?.factor}
          betting={home?.betting}
        />
      </div>

      {expanded && (
        <div id={panelId} className={styles.wxRowDetails}>
          <p className={styles.wxRowExplain}>{factor.explanation}</p>
        </div>
      )}
    </section>
  );
};

// A team's betting posture from the score model: a signed spread + O/U line,
// plus a home/away tag. Framed as market context, next to the factor edges.
const BettingPosture = ({ betting, isHome }) => {
  if (!betting) return null;
  const { spread, over_under: ou } = betting;
  let label = "Pick 'em";
  let cls = styles.posturePick;
  if (spread != null && spread > 0) {
    label = `Favored by ${spread}`;
    cls = styles.postureFav;
  } else if (spread != null && spread < 0) {
    label = `Underdog by ${Math.abs(spread)}`;
    cls = styles.postureDog;
  }
  return (
    <div className={styles.postureRow}>
      {isHome != null && (
        <span className={styles.postureSide}>{isHome ? "Home" : "Away"}</span>
      )}
      <span className={`${styles.postureBadge} ${cls}`}>{label}</span>
      {ou != null && <span className={styles.postureOu}>O/U {ou}</span>}
    </div>
  );
};

// One tone-coded edge section ("Working for them" / "Working against them").
const EdgeGroup = ({ title, tone, factors }) => {
  if (!factors.length) return null;
  return (
    <section className={styles.edgeGroup}>
      <h3 className={`${styles.edgeHeading} ${styles[tone]}`}>{title}</h3>
      <div className={styles.factorList}>
        {byScore(factors).map((factor, i) => (
          <FactorCard key={`${tone}-${i}`} factor={factor} />
        ))}
      </div>
    </section>
  );
};

// One team's column: betting posture + factors split into what helps vs hurts.
const TeamFactorDeck = ({ team }) => {
  // Weather is shown once, above, in the shared WeatherRow — exclude it here so
  // it isn't duplicated per team. These columns hold team-specific factors
  // (injury/news/…) as they come online.
  const factors = (team.factors || []).filter((f) => f.category !== "weather");
  const tailwinds = factors.filter((f) => f.direction === "tailwind");
  const headwinds = factors.filter((f) => f.direction === "headwind");
  const asOf = formatTimestamp(team.as_of_timestamp);

  return (
    <div className={styles.teamColumn}>
      <div className={styles.teamColumnHeader}>
        <TeamLogo teamName={team.team_name} size="medium" />
        <div className={styles.teamColumnHeaderText}>
          <h2 className={styles.teamColumnName}>{team.team_name || "Unknown team"}</h2>
          <BettingPosture betting={team.betting} isHome={team.is_home} />
        </div>
      </div>

      {factors.length === 0 ? (
        <p className={styles.noFactors}>
          No team-specific factors yet — injury &amp; news signals land here.
        </p>
      ) : (
        <>
          <EdgeGroup title="Working for them" tone="toneGood" factors={tailwinds} />
          <EdgeGroup title="Working against them" tone="toneBad" factors={headwinds} />
        </>
      )}

      {asOf && <span className={styles.asOf}>As of {asOf}</span>}
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
            {polymarket && polymarket.home_win_prob != null ? (
              <>
                <div className={styles.referenceScoreRow}>
                  <span className={styles.referenceScore}>
                    {pct(polymarket.home_win_prob) ?? "–"}
                  </span>
                  <span className={styles.referenceDetail}>
                    {polymarket.home_team || "Home"} win
                  </span>
                </div>
                {polymarket.market_type === "3way" && (
                  <div className={styles.referenceScoreRow}>
                    <span className={styles.referenceScore}>
                      {pct(polymarket.draw_prob) ?? "–"}
                    </span>
                    <span className={styles.referenceDetail}>Draw</span>
                  </div>
                )}
                <div className={styles.referenceScoreRow}>
                  <span className={styles.referenceScore}>
                    {pct(polymarket.away_win_prob) ?? "–"}
                  </span>
                  <span className={styles.referenceDetail}>
                    {polymarket.away_team || "Away"} win
                  </span>
                </div>
              </>
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
              {(state.data.away_team || state.data.home_team) && (
                <p className={styles.matchupLine}>
                  {state.data.away_team} <span className={styles.matchupAt}>@</span>{" "}
                  {state.data.home_team}
                </p>
              )}

              {(() => {
                const home = teams.find((t) => t.is_home === true);
                const away = teams.find((t) => t.is_home === false);
                const side = (t) => {
                  const f = (t?.factors || []).find(
                    (fa) => fa.category === "weather"
                  );
                  return f
                    ? { teamName: t.team_name, factor: f, betting: t.betting }
                    : null;
                };
                return <WeatherRow away={side(away)} home={side(home)} />;
              })()}

              {teams.length === 0 ? (
                <div className={styles.stateBox}>
                  <p>No team factor decks found for this game.</p>
                </div>
              ) : (
                <div className={styles.teamsGrid}>
                  {teams.map((team) => (
                    <TeamFactorDeck
                      key={team.team_id || team.team_name}
                      team={team}
                    />
                  ))}
                </div>
              )}

              <ReferencePanels panels={state.data.reference_panels} />
            </>
          )}
        </div>
      </main>
    </div>
  );
};

export default MatchupPage;
