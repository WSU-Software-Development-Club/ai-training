import React, { useEffect } from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  useLocation,
  useNavigationType,
} from "react-router-dom";
import HomePage from "./pages/HomePage";
import RankingsPage from "./pages/RankingsPage";
import StatsPage from "./pages/StatsPage";
import TeamsPage from "./pages/TeamsPage";
import ComparisonPage from "./pages/ComparisonPage";
import PredictionPage from "./pages/PredictionPage";
import TeamPage from "./pages/TeamPage";
import MatchupPage from "./pages/MatchupPage";
import Header from "./components/Header";
import { appConfig } from "./constants";
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

// Resets the window scroll to the top when navigating to a new route (e.g.
// clicking a game card while scrolled partway down the Home grid should land at
// the top of the Matchup page, not carry the old scroll offset over). Only acts
// on fresh PUSH/REPLACE navigations — on POP (browser back/forward) it does
// nothing, so the browser's native scroll restoration returns you to where you
// were. Renders nothing.
function ScrollToTop() {
  const { pathname } = useLocation();
  const navigationType = useNavigationType();

  useEffect(() => {
    if (navigationType !== "POP") {
      window.scrollTo(0, 0);
    }
  }, [pathname, navigationType]);

  return null;
}

// Wraps the routed page in a container keyed by pathname, so each navigation
// remounts it and replays a short fade-in (see `.pageFade` in index.css).
// Keyed on pathname only, so in-page state changes (filters, week) don't fade.
// Deliberately does NOT include the Header/Navigation — those live once in
// <App> outside of <Routes> so they never remount (and the logo never
// re-decodes/blinks) when navigating between tabs.
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

  // Placeholder search handler shared by the single, persistent Header — no
  // page currently wires up real search behavior (see TODOs on each page).
  const handleSearch = (searchTerm) => {
    console.log("Searching for:", searchTerm);
  };

  return (
    <Router>
      <RoutePrefetcher />
      <ScrollToTop />
      <div className="app">
        {/* Persistent chrome: rendered once, outside <Routes>, so the nav bar
            and logo stay mounted (no remount/re-decode blink) across every
            navigation. Only the content below it swaps per route. */}
        <Header title={appConfig.name} onSearch={handleSearch} />
        <AnimatedRoutes />
      </div>
    </Router>
  );
}

export default App;
