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

const Navigation = () => {
  const location = useLocation();
  const tabsRef = useRef(null);
  const tabRefs = useRef([]);
  // Navigation is rendered once, outside <Routes>, as part of the persistent
  // Header in App.jsx — it never unmounts on navigation, so plain state (no
  // module-scope persistence) already survives route changes. This ref just
  // distinguishes the very first mount from later re-renders triggered by a
  // navigation, so the indicator can start in place (no slide-in from the
  // origin) the first time, then glide FROM the previous tab TO the new one
  // on every navigation after that.
  const hasMountedRef = useRef(false);
  const [indicator, setIndicator] = useState({ left: 0, width: 0, visible: false });
  const [animate, setAnimate] = useState(false);

  const activeIndex = NAV_ITEMS.findIndex(
    (item) => item.to === location.pathname
  );

  // Measure the active tab and move the shared underline/pill to sit under it.
  const updateIndicator = useCallback(() => {
    const el = activeIndex >= 0 ? tabRefs.current[activeIndex] : null;
    if (el) {
      setIndicator({ left: el.offsetLeft, width: el.offsetWidth, visible: true });
    } else {
      // No matching tab (e.g. on a team detail page): keep last position but
      // fade the indicator out.
      setIndicator((prev) => ({ ...prev, visible: false }));
    }
  }, [activeIndex]);

  // Position the indicator. On the first-ever mount, do it synchronously before
  // paint so it appears in place (no slide from origin). On every later
  // render (a navigation), the state still holds the previous tab's position,
  // so defer the move to the next frame — that lets the old position paint
  // first, and the change to the new tab animates.
  useLayoutEffect(() => {
    if (hasMountedRef.current) {
      const id = requestAnimationFrame(() => updateIndicator());
      return () => cancelAnimationFrame(id);
    }
    updateIndicator();
    hasMountedRef.current = true;
  }, [updateIndicator]);

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
        <div className={styles.navigationTabs} ref={tabsRef}>
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
