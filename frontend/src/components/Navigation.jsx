import React from "react";
import { Link, useLocation } from "react-router-dom";
import "../styles/components/Navigation.css";

const Navigation = () => {
  const location = useLocation();

  const isActive = (path) => {
    return location.pathname === path;
  };

  return (
    <nav className="navigation">
      <div className="navigation__container">
        <div className="navigation__tabs">
          <Link
            to="/"
            className={`navigation__tab ${
              isActive("/") ? "navigation__tab--active" : ""
            }`}
          >
            Home
          </Link>
          <Link
            to="/stats"
            className={`navigation__tab ${
              isActive("/stats") ? "navigation__tab--active" : ""
            }`}
          >
            Stats
          </Link>
          <Link
            to="/rankings"
            className={`navigation__tab ${
              isActive("/rankings") ? "navigation__tab--active" : ""
            }`}
          >
            Rankings
          </Link>
          <Link
            to="/teams"
            className={`navigation__tab ${
              isActive("/teams") ? "navigation__tab--active" : ""
            }`}
          >
            Teams
          </Link>
          <Link
            to="/comparison"
            className={`navigation__tab ${
              isActive("/comparison") ? "navigation__tab--active" : ""
            }`}
          >
            Team Comparison
          </Link>
          <Link
            to="/prediction"
            className={`navigation__tab ${
              isActive("/prediction") ? "navigation__tab--active" : ""
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
