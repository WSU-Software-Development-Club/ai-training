import React, { useMemo, useState, useCallback } from "react";
import styles from "../styles/components/PolymarketHistoryChart.module.css";

// Historical Polymarket implied-win-probability chart for a finished game,
// shown in the Post-Game tab under the final score. The backend serves a dense
// per-minute in-game curve merged with a coarse multi-day pre-game context, so
// the chart DEFAULTS to the game window (an hour before kickoff → end) and lets
// you zoom OUT to the full pre-game drift, mirroring Polymarket's own view.
//
// Colors are the two brand hues, validated as a colorblind-safe categorical pair
// against the dark chart surface: home = crimson, away = cyan. Identity is
// carried by the legend AND a direct end-label, never color alone.
const HOME_COLOR = "#f43f5e"; // brand crimson (--color-primary)
const AWAY_COLOR = "#199aae"; // brand cyan, darkened to clear the dark band

const W = 720;
const H = 260;
const PAD = { top: 16, right: 60, bottom: 30, left: 44 };
const PLOT_W = W - PAD.left - PAD.right;
const PLOT_H = H - PAD.top - PAD.bottom;

const HOUR = 3600e3;
const DAY = 24 * HOUR;

const pct = (p) => `${Math.round(p * 100)}%`;

// Adaptive x-tick formatting: intraday windows show clock time, wider ones show
// the date (optionally with the hour) so labels stay legible at any zoom.
const makeTickFmt = (spanMs) => {
  if (spanMs <= 18 * HOUR) {
    return (ms) =>
      new Date(ms).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
  }
  if (spanMs <= 3 * DAY) {
    return (ms) =>
      new Date(ms).toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "numeric",
      });
  }
  return (ms) =>
    new Date(ms).toLocaleDateString(undefined, { month: "short", day: "numeric" });
};

const fmtFull = (ms) =>
  new Date(ms).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });

const PolymarketHistoryChart = ({ points, homeTeam, awayTeam, sourceUrl, kickoff }) => {
  const [hoverIdx, setHoverIdx] = useState(null);

  // Normalize once: parse timestamps, keep numeric probs, sort ascending.
  const series = useMemo(
    () =>
      (points || [])
        .map((p) => ({
          t: p.as_of ? new Date(p.as_of).getTime() : null,
          home: typeof p.home_win_prob === "number" ? p.home_win_prob : null,
          away: typeof p.away_win_prob === "number" ? p.away_win_prob : null,
        }))
        .filter((p) => p.t != null && (p.home != null || p.away != null))
        .sort((a, b) => a.t - b.t),
    [points]
  );

  const bounds = useMemo(() => {
    if (series.length === 0) return null;
    const tMin = series[0].t;
    const tMax = series[series.length - 1].t;
    const kickoffMs = kickoff ? new Date(kickoff).getTime() : null;
    // Default to JUST the game: from shortly before kickoff to the end of the
    // (already flat-tail-trimmed) curve, i.e. game start → 100%. Zooming out to
    // the pre-game drift is a preset away.
    const defaultStart =
      kickoffMs != null ? Math.max(tMin, kickoffMs - 0.5 * HOUR) : tMin;
    return { tMin, tMax, kickoffMs, defaultStart };
  }, [series, kickoff]);

  // The visible time window [start, end]; starts on the game view.
  const [view, setView] = useState(null);
  const activeView = useMemo(
    () => view || (bounds ? { start: bounds.defaultStart, end: bounds.tMax } : null),
    [view, bounds]
  );

  // Preset windows anchored to the game's end (data end) so "zoom out" reveals
  // more pre-game history. Only offer a preset if the data actually spans it.
  const presets = useMemo(() => {
    if (!bounds) return [];
    const { tMin, tMax, defaultStart } = bounds;
    const span = tMax - tMin;
    const all = [
      { key: "game", label: "Game", start: defaultStart },
      { key: "6h", label: "6H", start: tMax - 6 * HOUR },
      { key: "1d", label: "1D", start: tMax - DAY },
      { key: "max", label: "Max", start: tMin },
    ];
    return all.filter(
      (p) => p.key === "game" || p.key === "max" || tMax - p.start <= span + 1
    );
  }, [bounds]);

  const applyPreset = useCallback(
    (p) => setView({ start: Math.max(bounds.tMin, p.start), end: bounds.tMax }),
    [bounds]
  );

  const pan = useCallback(
    (dir) => {
      if (!activeView || !bounds) return;
      const width = activeView.end - activeView.start;
      const step = width * 0.4 * dir;
      let start = activeView.start + step;
      let end = activeView.end + step;
      if (start < bounds.tMin) {
        start = bounds.tMin;
        end = start + width;
      }
      if (end > bounds.tMax) {
        end = bounds.tMax;
        start = end - width;
      }
      setView({ start, end });
    },
    [activeView, bounds]
  );

  const geom = useMemo(() => {
    if (!activeView) return null;
    const { start, end } = activeView;
    const span = Math.max(1, end - start);
    const x = (t) => PAD.left + ((t - start) / span) * PLOT_W;
    const y = (p) => PAD.top + (1 - p) * PLOT_H;
    const visible = series.filter((pt) => pt.t >= start && pt.t <= end);
    return { start, end, span, x, y, visible };
  }, [activeView, series]);

  if (series.length === 0) {
    return <div className={styles.empty}>No Polymarket market for this game.</div>;
  }

  const { start, end, span, x, y, visible } = geom;
  const tickFmt = makeTickFmt(span);

  // Path for one team, breaking the line across null points.
  const linePath = (key) => {
    let d = "";
    let penUp = true;
    for (const pt of visible) {
      const v = pt[key];
      if (v == null) {
        penUp = true;
        continue;
      }
      d += `${penUp ? "M" : "L"}${x(pt.t).toFixed(1)} ${y(v).toFixed(1)} `;
      penUp = false;
    }
    return d.trim();
  };

  const yTicks = [0, 0.25, 0.5, 0.75, 1];
  const xTickMs = [start, start + span / 2, end];
  const last = visible[visible.length - 1] || series[series.length - 1];

  // Current preset (for button highlighting).
  const activeKey = (() => {
    for (const p of presets) {
      if (Math.abs(Math.max(bounds.tMin, p.start) - start) < 60e3 && end === bounds.tMax) {
        return p.key;
      }
    }
    return null;
  })();

  const onMove = (e) => {
    if (visible.length === 0) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const svgX = ((e.clientX - rect.left) / rect.width) * W;
    let best = 0;
    let bestD = Infinity;
    visible.forEach((pt, i) => {
      const dd = Math.abs(x(pt.t) - svgX);
      if (dd < bestD) {
        bestD = dd;
        best = i;
      }
    });
    setHoverIdx(best);
  };

  const hover = hoverIdx != null ? visible[hoverIdx] : null;

  return (
    <figure className={styles.figure}>
      <figcaption className={styles.caption}>
        <span className={styles.title}>Polymarket win probability</span>
        <div className={styles.legend} aria-hidden="true">
          <span className={styles.legendItem}>
            <span className={styles.swatch} style={{ background: HOME_COLOR }} />
            {homeTeam || "Home"}
          </span>
          <span className={styles.legendItem}>
            <span className={styles.swatch} style={{ background: AWAY_COLOR }} />
            {awayTeam || "Away"}
          </span>
        </div>
      </figcaption>

      {/* Zoom presets + pan navigation */}
      <div className={styles.controls}>
        <div className={styles.pan}>
          <button
            type="button"
            className={styles.panBtn}
            onClick={() => pan(-1)}
            disabled={start <= bounds.tMin}
            aria-label="Pan earlier"
          >
            ‹
          </button>
          <button
            type="button"
            className={styles.panBtn}
            onClick={() => pan(1)}
            disabled={end >= bounds.tMax}
            aria-label="Pan later"
          >
            ›
          </button>
        </div>
        <div className={styles.presets} role="group" aria-label="Zoom range">
          {presets.map((p) => (
            <button
              key={p.key}
              type="button"
              className={`${styles.presetBtn} ${activeKey === p.key ? styles.presetActive : ""}`}
              onClick={() => applyPreset(p)}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      <div className={styles.plot}>
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className={styles.svg}
          role="img"
          aria-label={`Polymarket implied win probability over time for ${
            homeTeam || "home"
          } versus ${awayTeam || "away"}`}
          onMouseMove={onMove}
          onMouseLeave={() => setHoverIdx(null)}
        >
          {yTicks.map((t) => (
            <g key={t}>
              <line
                x1={PAD.left}
                x2={W - PAD.right}
                y1={y(t)}
                y2={y(t)}
                className={t === 0.5 ? styles.gridMid : styles.grid}
              />
              <text x={PAD.left - 8} y={y(t)} className={styles.yLabel}>
                {pct(t)}
              </text>
            </g>
          ))}

          {xTickMs.map((ms, i) => (
            <text
              key={i}
              x={Math.min(W - PAD.right, Math.max(PAD.left, x(ms)))}
              y={H - 10}
              className={styles.xLabel}
              style={{ textAnchor: i === 0 ? "start" : i === xTickMs.length - 1 ? "end" : "middle" }}
            >
              {tickFmt(ms)}
            </text>
          ))}

          <path d={linePath("away")} className={styles.line} style={{ stroke: AWAY_COLOR }} />
          <path d={linePath("home")} className={styles.line} style={{ stroke: HOME_COLOR }} />

          {last?.away != null && (
            <text x={W - PAD.right + 8} y={y(last.away)} className={styles.endLabel} style={{ fill: AWAY_COLOR }}>
              {pct(last.away)}
            </text>
          )}
          {last?.home != null && (
            <text x={W - PAD.right + 8} y={y(last.home)} className={styles.endLabel} style={{ fill: HOME_COLOR }}>
              {pct(last.home)}
            </text>
          )}

          {hover && (
            <g pointerEvents="none">
              <line x1={x(hover.t)} x2={x(hover.t)} y1={PAD.top} y2={H - PAD.bottom} className={styles.crosshair} />
              {hover.away != null && (
                <circle cx={x(hover.t)} cy={y(hover.away)} r="4.5" fill={AWAY_COLOR} className={styles.dot} />
              )}
              {hover.home != null && (
                <circle cx={x(hover.t)} cy={y(hover.home)} r="4.5" fill={HOME_COLOR} className={styles.dot} />
              )}
            </g>
          )}
        </svg>

        {hover && (
          <div
            className={styles.tooltip}
            style={{ left: `${(x(hover.t) / W) * 100}%`, top: `${(PAD.top / H) * 100}%` }}
          >
            <div className={styles.tooltipDate}>{fmtFull(hover.t)}</div>
            <div className={styles.tooltipRow}>
              <span className={styles.swatch} style={{ background: HOME_COLOR }} />
              <span className={styles.tooltipName}>{homeTeam || "Home"}</span>
              <span className={styles.tooltipVal}>{hover.home != null ? pct(hover.home) : "—"}</span>
            </div>
            <div className={styles.tooltipRow}>
              <span className={styles.swatch} style={{ background: AWAY_COLOR }} />
              <span className={styles.tooltipName}>{awayTeam || "Away"}</span>
              <span className={styles.tooltipVal}>{hover.away != null ? pct(hover.away) : "—"}</span>
            </div>
          </div>
        )}
      </div>

      <div className={styles.footnote}>
        Implied probability from the Polymarket market — an outside input, not the
        model's or the deck's verdict.
        {sourceUrl && (
          <>
            {" "}
            <a href={sourceUrl} target="_blank" rel="noopener noreferrer" className={styles.sourceLink}>
              View market ↗
            </a>
          </>
        )}
      </div>
    </figure>
  );
};

export default PolymarketHistoryChart;
