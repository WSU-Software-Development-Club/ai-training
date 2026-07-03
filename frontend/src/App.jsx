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

// Wraps the routed page in a plain layout container (see `.routeOutlet` in
// index.css — flex:1 so the page fills the space below the persistent
// header). Previously this div was keyed by pathname to force a remount and
// replay a fade-in animation on every navigation; that key made the wrapper
// itself (and everything inside it) tear down and rebuild on every nav,
// which is exactly what produced the visible flicker. No key, no animation:
// <Routes> still swaps the matched page normally, but nothing above it
// remounts or fades.
// Deliberately does NOT include the Header/Navigation — those live once in
// <App> outside of <Routes> so they never remount (and the logo never
// re-decodes/blinks) when navigating between tabs.
function AnimatedRoutes() {
  const location = useLocation();

  return (
    <div className="routeOutlet">
      <Routes location={location}>
        <Route path="/" element={<HomePage />} />
        <Route path="/rankings" element={<RankingsPage />} />
        <Route path="/stats" element={<StatsPage />} />
        <Route path="/teams" element={<TeamsPage />} />
        <Route path="/comparison" element={<ComparisonPage />} />
        <Route path="/prediction" element={<PredictionPage />} />
        <Route path="/team/:teamName" element={<TeamPage />} />
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
