import React from "react";
import { Link } from "react-router-dom";
import SearchBar from "./SearchBar";
import Navigation from "./Navigation";
import styles from "../styles/components/Header.module.css";

const Header = ({ title, onSearch }) => {
  return (
    <header className={styles.header}>
      <div className={styles.headerContainer}>
        <div className={styles.headerBranding}>
          <a
            href="https://wsu-swdc.dev/"
            target="_blank"
            rel="noopener noreferrer"
            className={styles.swdcLogoLink}
            aria-label="Visit WSU Software Development Club"
          >
            <img
              src="/swdc-logo.png"
              alt="WSU Software Development Club"
              className={styles.swdcLogo}
              width={50}
              height={50}
            />
          </a>
          <div className={styles.headerTitleContainer}>
            <h1 className={styles.headerTitle}>
              <Link
                to="/"
                className={styles.headerTitleLink}
                aria-label={`${title} — go to home`}
              >
                {title}
              </Link>
            </h1>
            {/**
            <p className={styles.headerSubtitle}>
              Subtitle here
            </p>
            */}
          </div>
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
