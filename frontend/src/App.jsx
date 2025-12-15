import React, { useEffect } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import HomePage from "./pages/HomePage";
import RankingsPage from "./pages/RankingsPage";
import StatsPage from "./pages/StatsPage";
import TeamsPage from "./pages/TeamsPage";
import ComparisonPage from "./pages/ComparisonPage";
import PredictionPage from "./pages/PredictionPage";
import { preloadTeamData } from "./branding/teamBranding";
import "./App.css";

function App() {
  // Preload team branding data on app initialization
  useEffect(() => {
    preloadTeamData().catch((error) => {
      console.error("Failed to preload team data:", error);
    });
  }, []);

  return (
    <Router>
      <div className="app">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/rankings" element={<RankingsPage />} />
          <Route path="/stats" element={<StatsPage />} />
          <Route path="/teams" element={<TeamsPage />} />
          <Route path="/comparison" element={<ComparisonPage />} />
          <Route path="/prediction" element={<PredictionPage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
