import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { FiSearch } from "react-icons/fi";
import { findTeamByName } from "../matching/teamMatcher";
import api from "../services/api";
import TeamLogo from "./TeamLogo";
import { navigateToTeam } from "../utils/teamNavigation";
import styles from "../styles/components/SearchBar.module.css";

const SearchBar = ({ onSearch, placeholder = "Search teams" }) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [teams, setTeams] = useState([]);
  const [filteredTeams, setFilteredTeams] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const navigate = useNavigate();
  const searchBarRef = useRef(null);
  const suggestionsRef = useRef(null);

  // Fetch teams on mount
  useEffect(() => {
    const fetchTeams = async () => {
      try {
        const response = await api.getAllTeams();
        if (response.success && response.data) {
          setTeams(response.data);
        }
      } catch (error) {
        console.error("Error fetching teams:", error);
      }
    };
    fetchTeams();
  }, []);

  // Filter teams based on search term
  useEffect(() => {
    if (!searchTerm.trim()) {
      setFilteredTeams([]);
      setShowSuggestions(false);
      return;
    }

    const term = searchTerm.toLowerCase().trim();
    const filtered = teams
      .filter((team) => {
        const teamName = (team.name || "").toLowerCase();
        return teamName.includes(term);
      })
      .slice(0, 10); // Limit to 10 suggestions

    setFilteredTeams(filtered);
    setShowSuggestions(filtered.length > 0);
    setSelectedIndex(-1);
  }, [searchTerm, teams]);

  // Handle clicks outside to close suggestions
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        searchBarRef.current &&
        !searchBarRef.current.contains(event.target)
      ) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  // Highlight matching text in team name
  const highlightMatch = (teamName, searchTerm) => {
    if (!searchTerm.trim()) return teamName;

    // Escape special regex characters in search term
    const escapedTerm = searchTerm.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const regex = new RegExp(`(${escapedTerm})`, "gi");
    const parts = teamName.split(regex);

    // When splitting with a capturing group, matches are at odd indices
    return parts.map((part, index) => {
      // Check if this part matches the search term (case-insensitive)
      const isMatch = part.toLowerCase() === searchTerm.toLowerCase();
      return isMatch ? (
        <strong key={index}>{part}</strong>
      ) : (
        <span key={index}>{part}</span>
      );
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!searchTerm.trim()) {
      return;
    }

    // If a suggestion is selected, navigate to it
    if (selectedIndex >= 0 && filteredTeams[selectedIndex]) {
      const team = filteredTeams[selectedIndex];
      navigateToTeam(navigate, team.name);
      setSearchTerm("");
      setShowSuggestions(false);
      return;
    }

    // Try to find the team using the team matcher
    try {
      const team = await findTeamByName(searchTerm.trim());

      if (team) {
        // Navigate to the team page
        const encodedTeamName = encodeURIComponent(team.school);
        navigate(`/team/${encodedTeamName}`);
        setSearchTerm(""); // Clear search after navigation
        setShowSuggestions(false);
      } else {
        // If team not found, call the onSearch callback (for any custom handling)
        if (onSearch) {
          onSearch(searchTerm);
        }
        // Optionally show a message that team wasn't found
        console.log("Team not found:", searchTerm);
      }
    } catch (error) {
      console.error("Error searching for team:", error);
      if (onSearch) {
        onSearch(searchTerm);
      }
    }
  };

  const handleChange = (e) => {
    setSearchTerm(e.target.value);
  };

  const handleTeamClick = (team) => {
    navigateToTeam(navigate, team.name);
    setSearchTerm("");
    setShowSuggestions(false);
  };

  const handleKeyDown = (e) => {
    if (!showSuggestions || filteredTeams.length === 0) {
      if (e.key === "Enter") {
        handleSubmit(e);
      }
      return;
    }

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev < filteredTeams.length - 1 ? prev + 1 : prev
        );
        break;
      case "ArrowUp":
        e.preventDefault();
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : -1));
        break;
      case "Enter":
        e.preventDefault();
        if (selectedIndex >= 0 && filteredTeams[selectedIndex]) {
          handleTeamClick(filteredTeams[selectedIndex]);
        } else {
          handleSubmit(e);
        }
        break;
      case "Escape":
        setShowSuggestions(false);
        setSelectedIndex(-1);
        break;
      default:
        break;
    }
  };

  return (
    <div className={styles.searchBarWrapper} ref={searchBarRef}>
      <form className={styles.searchBar} onSubmit={handleSubmit}>
        <div className={styles.searchBarContainer}>
          <div className={styles.searchBarIcon}>
            <FiSearch size={20} />
          </div>
          <input
            type="text"
            className={styles.searchBarInput}
            placeholder={placeholder}
            value={searchTerm}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            onFocus={() => {
              if (filteredTeams.length > 0) {
                setShowSuggestions(true);
              }
            }}
          />
        </div>
      </form>
      {showSuggestions && filteredTeams.length > 0 && (
        <div className={styles.suggestions} ref={suggestionsRef}>
          {filteredTeams.map((team, index) => (
            <div
              key={team.id || team.name}
              className={`${styles.suggestionItem} ${
                index === selectedIndex ? styles.suggestionItemSelected : ""
              }`}
              onClick={() => handleTeamClick(team)}
              onMouseEnter={() => setSelectedIndex(index)}
            >
              <div className={styles.suggestionLogo}>
                <TeamLogo teamName={team.name} size="small" />
              </div>
              <div className={styles.suggestionName}>
                {highlightMatch(team.name, searchTerm)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SearchBar;
