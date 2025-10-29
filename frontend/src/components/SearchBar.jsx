import React, { useState } from "react";
import styles from "../styles/components/SearchBar.module.css";

const SearchBar = ({ onSearch, placeholder = "Search teams, games..." }) => {
  const [searchTerm, setSearchTerm] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    // TODO: Replace with API call to /api/search
    console.log("Search term:", searchTerm);
    if (onSearch) {
      onSearch(searchTerm);
    }
  };

  const handleChange = (e) => {
    setSearchTerm(e.target.value);
  };

  return (
    <form className={styles.searchBar} onSubmit={handleSubmit}>
      <div className={styles.searchBarContainer}>
        <div className={styles.searchBarIcon}>
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M21 21L16.514 16.506L21 21ZM19 10.5C19 15.194 15.194 19 10.5 19C5.806 19 2 15.194 2 10.5C2 5.806 5.806 2 10.5 2C15.194 2 19 5.806 19 10.5Z"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
        <input
          type="text"
          className={styles.searchBarInput}
          placeholder={placeholder}
          value={searchTerm}
          onChange={handleChange}
        />
      </div>
    </form>
  );
};

export default SearchBar;
