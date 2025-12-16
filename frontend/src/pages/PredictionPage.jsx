import React from "react";
import { FiBarChart2 } from "react-icons/fi";
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
                <FiBarChart2 size={64} />
              </div>
              <h2 className={styles.predictionPagePlaceholderTitle}>
                Coming Soon
              </h2>
              <p className={styles.predictionPagePlaceholderText}>
                This page is under development. It will show how the prediciton
                model works.
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
