import React from "react";
import SearchBar from "./SearchBar";
import Navigation from "./Navigation";
import "../styles/components/Header.css";

const Header = ({ title, onSearch }) => {
  return (
    <header className="header">
      <div className="header__container">
        <div className="header__branding">
          <h1 className="header__title">{title}</h1>
          <p className="header__subtitle">College Football Scores & Rankings</p>
        </div>
        <div className="header__search">
          <SearchBar onSearch={onSearch} />
        </div>
      </div>
      <Navigation />
    </header>
  );
};

export default Header;
