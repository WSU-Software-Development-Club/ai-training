import React from "react";
import SearchBar from "./SearchBar";
import Navigation from "./Navigation";
import styles from "../styles/components/Header.module.css";

const Header = ({ title, onSearch }) => {
  return (
    <header className={styles.header}>
      <div className={styles.headerContainer}>
        <div className={styles.headerBranding}>
          <h1 className={styles.headerTitle}>{title}</h1>
          <p className={styles.headerSubtitle}>
            College Football Scores & Rankings
          </p>
        </div>
        <div className={styles.headerSearch}>
          <SearchBar onSearch={onSearch} />
        </div>
      </div>
      <Navigation />
    </header>
  );
};

export default Header;
