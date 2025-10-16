import React, { useState, useEffect } from "react";
import Header from "../components/Header";
import RankingsTable from "../components/RankingsTable";
import { appConfig } from "../constants";
import api from "../services/api";
import "../styles/pages/RankingsPage.css";

const RankingsPage = () => {
  const [ranking, setRanking] = useState(null); // single ranking
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const handleSearch = (searchTerm) => {
    console.log("Searching for:", searchTerm);
  };
  useEffect(() => {
    const fetchRanking = async () => {
      try {
        const response = await api.getRankings(); // <-- use a named variable
        console.log("API response:", response.data) /* DEBUGGING PURPOSES */
        if (response.success) {
          setRanking(response.data);
        } else {
          setError("No rankings available");
        }
      } catch (err) {
        console.error(err);
        setError("Unable to load rankings.");
      } finally {
        setLoading(false);
      }
    };

    fetchRanking();
  }, []);

  return (
    <div className="rankings-page">
      <Header title={appConfig.name} onSearch={handleSearch} />

      <main className="rankings-page__main">
        <div className="rankings-page__container">
          <div className="rankings-page__header">
            <h1 className="rankings-page__title">AP Top 25 Rankings</h1>
            <p className="rankings-page__subtitle">
              Current Associated Press College Football Rankings
            </p>
          </div>

          <div className="rankings-page__content">
            {loading && <p>Loading rankings...</p>}
            {error && <p className="error">{error}</p>}
            {ranking && (
              <RankingsTable rankings={ranking.data} title="AP Top 25" />
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default RankingsPage;
