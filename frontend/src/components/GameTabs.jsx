import React, { useId, useState } from "react";
import PreGamePanel from "./PreGamePanel";
import LivePanel from "./LivePanel";
import PostGamePanel from "./PostGamePanel";
import styles from "../styles/components/GameTabs.module.css";

// Three-tab shell for a single game's matchup views. UI-only: the active tab is
// local state defaulting to "pre" (manual click to switch — no routing, no URL
// params, and no status-driven auto-selection yet). `gameId` and the fetched
// `matchup` state are threaded down to each panel; only the Post-Game panel
// consumes `matchup` today (Pre-Game and Live ignore both).
const TABS = [
  { key: "pre", label: "Pre-Game", Panel: PreGamePanel },
  { key: "live", label: "Live", Panel: LivePanel },
  { key: "post", label: "Post-Game", Panel: PostGamePanel },
];

const GameTabs = ({ gameId, matchup, initialTab }) => {
  // Default to Pre-Game unless a caller (e.g. a finished-game card) passes a
  // valid initial tab like "post".
  const [active, setActive] = useState(() =>
    TABS.some((t) => t.key === initialTab) ? initialTab : "pre"
  );
  const baseId = useId();

  return (
    <div className={styles.gameTabs}>
      <div className={styles.tabList} role="tablist" aria-label="Game views">
        {TABS.map(({ key, label }) => {
          const selected = key === active;
          return (
            <button
              key={key}
              type="button"
              role="tab"
              id={`${baseId}-tab-${key}`}
              aria-selected={selected}
              aria-controls={`${baseId}-panel-${key}`}
              tabIndex={selected ? 0 : -1}
              className={`${styles.tab} ${selected ? styles.tabActive : ""}`}
              onClick={() => setActive(key)}
            >
              {label}
            </button>
          );
        })}
      </div>

      {TABS.map(({ key, Panel }) => {
        const selected = key === active;
        return (
          <div
            key={key}
            role="tabpanel"
            id={`${baseId}-panel-${key}`}
            aria-labelledby={`${baseId}-tab-${key}`}
            hidden={!selected}
          >
            {selected && <Panel gameId={gameId} matchup={matchup} />}
          </div>
        );
      })}
    </div>
  );
};

export default GameTabs;
