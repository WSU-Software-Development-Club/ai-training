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
  { to: "/stats", label: "Stats" },
  { to: "/rankings", label: "Rankings" },
  { to: "/teams", label: "Teams" },
  { to: "/comparison", label: "Team Comparison" },
];

const Navigation = () => {
  const location = useLocation();
  const tabRefs = useRef([]);
  const [indicator, setIndicator] = useState({
    left: 0,
    width: 0,
    visible: false,
  });
  // Transition is enabled only after the first position is set, so the
  // underline doesn't slide in from the left edge on initial load.
  const [animate, setAnimate] = useState(false);

  const activeIndex = NAV_ITEMS.findIndex(
    (item) => item.to === location.pathname
  );

  // Measure the active tab and move the shared underline to sit under it.
  const updateIndicator = useCallback(() => {
    const el = activeIndex >= 0 ? tabRefs.current[activeIndex] : null;
    if (el) {
      setIndicator({ left: el.offsetLeft, width: el.offsetWidth, visible: true });
    } else {
      // No matching tab (e.g. on a team detail page): keep last position but
      // fade the underline out.
      setIndicator((prev) => ({ ...prev, visible: false }));
    }
  }, [activeIndex]);

  useLayoutEffect(() => {
    updateIndicator();
  }, [updateIndicator]);

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

  return (
    <nav className={styles.navigation}>
      <div className={styles.navigationContainer}>
        <div className={styles.navigationTabs}>
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
          <span
            className={styles.navigationIndicator}
            style={{
              transform: `translateX(${indicator.left}px)`,
              width: `${indicator.width}px`,
              opacity: indicator.visible ? 1 : 0,
              transition: animate
                ? "transform 0.35s var(--ease-smooth), width 0.35s var(--ease-smooth), opacity 0.2s ease"
                : "none",
            }}
          />
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
