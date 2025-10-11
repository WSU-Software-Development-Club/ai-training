import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import HomePage from "./pages/HomePage";
import RankingsPage from "./pages/RankingsPage";
import StatsPage from "./pages/StatsPage";
import TeamsPage from "./pages/TeamsPage";
import ComparisonPage from "./pages/ComparisonPage";
import PredictionPage from "./pages/PredictionPage";
import "./App.css";

function App() {
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
