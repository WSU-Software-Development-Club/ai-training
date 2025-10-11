import React, { useState } from "react";
import Header from "../components/Header";
import StatsTable from "../components/StatsTable";
import { appConfig } from "../constants";
import { mockStats, statCategories } from "../utils/mockData";
import "../styles/pages/StatsPage.css";

const StatsPage = () => {
  const [selectedCategory, setSelectedCategory] = useState("Scoring Offense");

  const handleSearch = (searchTerm) => {
    // TODO: Replace with API call to /api/search
    console.log("Searching for:", searchTerm);
  };

  const currentStats = mockStats[selectedCategory] || [];

  return (
    <div className="stats-page">
      <Header title={appConfig.name} onSearch={handleSearch} />

      <main className="stats-page__main">
        <div className="stats-page__container">
          <div className="stats-page__header">
            <h1 className="stats-page__title">Team Statistics</h1>
            <p className="stats-page__subtitle">
              View team statistics across different categories
            </p>
          </div>

          <div className="stats-page__filters">
            <div className="stats-page__filter-group">
              <label className="stats-page__filter-label">Stat Category:</label>
              <select
                className="stats-page__filter-select"
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
              >
                {statCategories.map((category) => (
                  <option key={category} value={category}>
                    {category}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="stats-page__content">
            <StatsTable
              stats={currentStats}
              title={selectedCategory}
              statCategory={selectedCategory}
            />

            {/* TODO: Replace mockStats with API call to /api/stats */}
            {/* Hint: Use useState, useEffect, and fetch API */}
            {/* 
            Example API integration:
            const [stats, setStats] = useState([]);
            const [loading, setLoading] = useState(true);
            
            useEffect(() => {
              const fetchStats = async () => {
                try {
                  const response = await fetch(`/api/stats/${selectedCategory}`);
                  const data = await response.json();
                  if (data.success) {
                    setStats(data.data);
                  }
                } catch (error) {
                  console.error('Error fetching stats:', error);
                } finally {
                  setLoading(false);
                }
              };
              fetchStats();
            }, [selectedCategory]);
            */}
          </div>
        </div>
      </main>
    </div>
  );
};

export default StatsPage;
