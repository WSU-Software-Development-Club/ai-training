import React, { useEffect } from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  useLocation,
} from "react-router-dom";
import HomePage from "./pages/HomePage";
import RankingsPage from "./pages/RankingsPage";
import StatsPage from "./pages/StatsPage";
import TeamsPage from "./pages/TeamsPage";
import ComparisonPage from "./pages/ComparisonPage";
import PredictionPage from "./pages/PredictionPage";
import TeamPage from "./pages/TeamPage";
import MatchupPage from "./pages/MatchupPage";
import { preloadTeamData } from "./branding/teamBranding";
import { prefetchForRoute } from "./services/prefetchService";
import "./App.css";
import { api } from "./services/api";

// Watches the active route and warms the response cache in the background:
// the rest of the current tab's data first, then the default data for every
// other tab. Renders nothing.
function RoutePrefetcher() {
  const location = useLocation();

  useEffect(() => {
    prefetchForRoute(location.pathname);
  }, [location.pathname]);

  return null;
}

// Wraps the routed page in a container keyed by pathname, so each navigation
// remounts it and replays a short fade-in (see `.pageFade` in index.css).
// Keyed on pathname only, so in-page state changes (filters, week) don't fade.
function AnimatedRoutes() {
  const location = useLocation();

  return (
    <div key={location.pathname} className="pageFade">
      <Routes location={location}>
        <Route path="/" element={<HomePage />} />
        <Route path="/rankings" element={<RankingsPage />} />
        <Route path="/stats" element={<StatsPage />} />
        <Route path="/teams" element={<TeamsPage />} />
        <Route path="/comparison" element={<ComparisonPage />} />
        <Route path="/prediction" element={<PredictionPage />} />
        <Route path="/team/:teamName" element={<TeamPage />} />
        <Route path="/matchup/:gameId" element={<MatchupPage />} />
      </Routes>
    </div>
  );
}

function App() {
  // Preload team branding data on app initialization
  useEffect(() => {
    preloadTeamData().catch((error) => {
      console.error("Failed to preload team data:", error);
    });
    api.getHealthStatus().catch(() => {
      console.log("Backend warming up...");
    });
  }, []);

  return (
    <Router>
      <RoutePrefetcher />
      <div className="app">
        <AnimatedRoutes />
      </div>
    </Router>
  );
}

export default App;
