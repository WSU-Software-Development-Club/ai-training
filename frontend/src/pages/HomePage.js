import React, { useState, useEffect } from "react";
import Header from "../components/Header";
import StatusCard from "../components/StatusCard";
import { api } from "../services/api";
import { appConfig } from "../constants";
import "./HomePage.css";

const HomePage = () => {
  const [message, setMessage] = useState("");
  const [health, setHealth] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        // Fetch data from backend using the API service
        const [messageData, healthData] = await Promise.all([
          api.getWelcomeMessage(),
          api.getHealthStatus(),
        ]);

        setMessage(messageData.message);
        setHealth(healthData.status);
      } catch (err) {
        console.error("Error fetching data:", err);
        setError("Failed to connect to backend");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  return (
    <div className="home-page">
      <Header
        title={appConfig.name}
        subtitle="A simple React and Flask application"
      />

      <main className="home-page__main">
        {loading ? (
          <div className="loading">
            <p>Loading...</p>
          </div>
        ) : error ? (
          <div className="error">
            <p>{error}</p>
          </div>
        ) : (
          <div className="status-grid">
            <StatusCard title="Backend Message" value={message} status="info" />
            <StatusCard
              title="Backend Status"
              value={health}
              status="success"
            />
          </div>
        )}
      </main>
    </div>
  );
};

export default HomePage;
