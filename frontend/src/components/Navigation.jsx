import React, {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { Link, useLocation } from "react-router-dom";
import styles from "../styles/components/Navigation.module.css";

const NAV_ITEMS = [
  { to: "/", label: "Home" },
  { to: "/prediction", label: "Predictions" },
  { to: "/stats", label: "Stats" },
  { to: "/rankings", label: "Rankings" },
  { to: "/teams", label: "Teams" },
  { to: "/comparison", label: "Team Comparison" },
];

// The Header (and this Navigation) remounts on every route change because each
// page renders its own <Header>. Persist state at module scope across those
// remounts:
//   - the tab row's horizontal scroll position, and
//   - the sliding indicator's last position, so on the next page it can animate
//     FROM the previously-active tab TO the new one (instead of just appearing).
let savedTabsScrollLeft = 0;
let savedIndicator = { left: 0, width: 0, visible: false };
let hasMountedOnce = false;

const Navigation = () => {
  const location = useLocation();
  const tabsRef = useRef(null);
  const tabRefs = useRef([]);
  // Seed from the persisted position so a navigation starts the underline/pill
  // at the previously-active tab, then slides it to the new one.
  const [indicator, setIndicator] = useState(savedIndicator);
  // Animate from the very first render on a navigation (we've mounted before);
  // on the first-ever mount, start without animating so it doesn't slide in
  // from the origin.
  const [animate, setAnimate] = useState(hasMountedOnce);

  const activeIndex = NAV_ITEMS.findIndex(
    (item) => item.to === location.pathname
  );

  // Measure the active tab and move the shared underline/pill to sit under it,
  // persisting the position so it survives the next remount.
  const updateIndicator = useCallback(() => {
    const el = activeIndex >= 0 ? tabRefs.current[activeIndex] : null;
    if (el) {
      const next = { left: el.offsetLeft, width: el.offsetWidth, visible: true };
      savedIndicator = next;
      setIndicator(next);
    } else {
      // No matching tab (e.g. on a team detail page): keep last position but
      // fade the indicator out.
      setIndicator((prev) => {
        const next = { ...prev, visible: false };
        savedIndicator = next;
        return next;
      });
    }
  }, [activeIndex]);

  // Position the indicator. On the first-ever mount, do it synchronously before
  // paint so it appears in place (no slide from origin). On later mounts (a
  // navigation) the state already holds the previous tab's position, so defer
  // the move to the next frame — that lets the old position paint first, and
  // the change to the new tab animates.
  useLayoutEffect(() => {
    if (hasMountedOnce) {
      const id = requestAnimationFrame(() => updateIndicator());
      return () => cancelAnimationFrame(id);
    }
    updateIndicator();
    hasMountedOnce = true;
  }, [updateIndicator]);

  // Restore the tab row's horizontal scroll position on mount (before paint)
  // so navigating between pages never makes the bar jump.
  useLayoutEffect(() => {
    const el = tabsRef.current;
    if (el) {
      el.scrollLeft = savedTabsScrollLeft;
    }
  }, []);

  const handleTabsScroll = (e) => {
    savedTabsScrollLeft = e.currentTarget.scrollLeft;
  };

  // Ensure animation is enabled shortly after the first mount, so later resizes
  // and font swaps animate too.
  useEffect(() => {
    const id = requestAnimationFrame(() => setAnimate(true));
    return () => cancelAnimationFrame(id);
  }, []);

  // Reposition on resize and once web fonts finish loading (tab widths shift
  // when the display font swaps in).
  useEffect(() => {
    window.addEventListener("resize", updateIndicator);
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(updateIndicator).catch(() => {});
    }
    return () => window.removeEventListener("resize", updateIndicator);
  }, [updateIndicator]);

  // Shared motion for the highlight pill and the underline so they glide
  // together between tabs.
  const glide = animate
    ? "transform 0.32s var(--ease-smooth), width 0.32s var(--ease-smooth), opacity 0.2s ease"
    : "none";
  const indicatorStyle = {
    transform: `translateX(${indicator.left}px)`,
    width: `${indicator.width}px`,
    opacity: indicator.visible ? 1 : 0,
    transition: glide,
  };

  return (
    <nav className={styles.navigation}>
      <div className={styles.navigationContainer}>
        <div
          className={styles.navigationTabs}
          ref={tabsRef}
          onScroll={handleTabsScroll}
        >
          {/* Sliding background highlight that glides behind the active tab. */}
          <span className={styles.navigationHighlight} style={indicatorStyle} />
          {NAV_ITEMS.map((item, index) => (
            <Link
              key={item.to}
              to={item.to}
              ref={(el) => (tabRefs.current[index] = el)}
              className={`${styles.navigationTab} ${
                location.pathname === item.to ? styles.navigationTabActive : ""
              }`}
            >
              {item.label}
            </Link>
          ))}
          {/* Single shared underline that glides between tabs on navigation. */}
          <span className={styles.navigationIndicator} style={indicatorStyle} />
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
