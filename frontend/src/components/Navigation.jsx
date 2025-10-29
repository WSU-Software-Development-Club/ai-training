import React from "react";
import { Link, useLocation } from "react-router-dom";
import styles from "../styles/components/Navigation.module.css";

const Navigation = () => {
  const location = useLocation();

  const isActive = (path) => {
    return location.pathname === path;
  };

  return (
    <nav className={styles.navigation}>
      <div className={styles.navigationContainer}>
        <div className={styles.navigationTabs}>
          <Link
            to="/"
            className={`${styles.navigationTab} ${
              isActive("/") ? styles.navigationTabActive : ""
            }`}
          >
            Home
          </Link>
          <Link
            to="/stats"
            className={`${styles.navigationTab} ${
              isActive("/stats") ? styles.navigationTabActive : ""
            }`}
          >
            Stats
          </Link>
          <Link
            to="/rankings"
            className={`${styles.navigationTab} ${
              isActive("/rankings") ? styles.navigationTabActive : ""
            }`}
          >
            Rankings
          </Link>
          <Link
            to="/teams"
            className={`${styles.navigationTab} ${
              isActive("/teams") ? styles.navigationTabActive : ""
            }`}
          >
            Teams
          </Link>
          <Link
            to="/comparison"
            className={`${styles.navigationTab} ${
              isActive("/comparison") ? styles.navigationTabActive : ""
            }`}
          >
            Team Comparison
          </Link>
          <Link
            to="/prediction"
            className={`${styles.navigationTab} ${
              isActive("/prediction") ? styles.navigationTabActive : ""
            }`}
          >
            Win Prediction
          </Link>
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
