import React from "react";
import Header from "../components/Header";
import { appConfig } from "../constants";
import styles from "../styles/pages/PredictionPage.module.css";

const PredictionPage = () => {
  const handleSearch = (searchTerm) => {
    // MOCK FUNCTIONALITY - Replace with actual search API call
    console.log("Searching for:", searchTerm);
  };

  return (
    <div className={styles.predictionPage}>
      <Header title={appConfig.name} onSearch={handleSearch} />

      <main className={styles.predictionPageMain}>
        <div className={styles.predictionPageContainer}>
          <div className={styles.predictionPageHeader}>
            <h1 className={styles.predictionPageTitle}>Win Prediction</h1>
            <p className={styles.predictionPageSubtitle}>
              Predict game outcomes using advanced analytics
            </p>
          </div>

          <div className={styles.predictionPageContent}>
            <div className={styles.predictionPagePlaceholder}>
              <div className={styles.predictionPagePlaceholderIcon}>
                <svg
                  width="64"
                  height="64"
                  viewBox="0 0 24 24"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M9.663 17H4.337C3.603 17 3 16.397 3 15.663V8.337C3 7.603 3.603 7 4.337 7H9.663C10.397 7 11 7.603 11 8.337V15.663C11 16.397 10.397 17 9.663 17Z"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <path
                    d="M21 17H15.337C14.603 17 14 16.397 14 15.663V8.337C14 7.603 14.603 7 15.337 7H21"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <path
                    d="M21 13H15"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>
              <h2 className={styles.predictionPagePlaceholderTitle}>
                Coming Soon
              </h2>
              <p className={styles.predictionPagePlaceholderText}>
                Win prediction feature is under development. This will use
                machine learning algorithms and historical data to predict game
                outcomes with confidence percentages.
              </p>

              {/* TODO: Implement win prediction functionality */}
              {/* Hint: Team selection, ML algorithm, confidence %, prediction history */}
              {/* Backend: /api/predictions, /api/games/upcoming, /api/weather, /api/injuries */}
              {/* ML: Historical data, feature engineering, model validation */}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default PredictionPage;
