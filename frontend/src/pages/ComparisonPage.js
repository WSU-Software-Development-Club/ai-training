import React from "react";
import Header from "../components/Header";
import { appConfig } from "../constants";
import "../styles/pages/ComparisonPage.css";

const ComparisonPage = () => {
  const handleSearch = (searchTerm) => {
    // MOCK FUNCTIONALITY - Replace with actual search API call
    console.log("Searching for:", searchTerm);
  };

  return (
    <div className="comparison-page">
      <Header title={appConfig.name} onSearch={handleSearch} />

      <main className="comparison-page__main">
        <div className="comparison-page__container">
          <div className="comparison-page__header">
            <h1 className="comparison-page__title">Team Comparison</h1>
            <p className="comparison-page__subtitle">
              Compare statistics between college football teams
            </p>
          </div>

          <div className="comparison-page__content">
            <div className="comparison-page__placeholder">
              <div className="comparison-page__placeholder-icon">
                <svg
                  width="64"
                  height="64"
                  viewBox="0 0 24 24"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M9 12L11 14L15 10M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>
              <h2 className="comparison-page__placeholder-title">
                Coming Soon
              </h2>
              <p className="comparison-page__placeholder-text">
                Team comparison feature is under development. This will allow
                you to compare statistics, records, and performance metrics
                between different college football teams.
              </p>

              {/* TODO: Implement team comparison functionality */}
              {/* Hint: Team selection, comparison layout, stats table, charts */}
              {/* Backend: /api/teams, /api/teams/:id/stats, /api/teams/:id1/vs/:id2 */}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default ComparisonPage;
