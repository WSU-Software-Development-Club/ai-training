import React, { useState } from "react";
import { useTeamBranding } from "../hooks/useTeamBranding";
import styles from "../styles/components/TeamLogo.module.css";

/**
 * TeamLogo Component
 *
 * Displays a team's logo with fallback handling for missing/broken images.
 * Supports light and dark mode variants.
 *
 * @param {string} teamName - The team name to display logo for
 * @param {string} variant - 'light' or 'dark' (default: 'light')
 * @param {string} size - Size class: 'small', 'medium', 'large' (default: 'medium')
 * @param {string} className - Additional CSS classes
 */
const TeamLogo = ({
  teamName,
  variant = "light",
  size = "medium",
  className = "",
}) => {
  const { branding, loading } = useTeamBranding(teamName);
  const [imageError, setImageError] = useState(false);

  // Determine which logo URL to use
  const logoUrl =
    variant === "dark" && branding?.logoDark
      ? branding.logoDark
      : branding?.logo;

  // Show placeholder if loading, no branding, or image error
  const showPlaceholder = loading || !branding || !logoUrl || imageError;

  const handleImageError = () => {
    setImageError(true);
  };

  const handleImageLoad = () => {
    setImageError(false);
  };

  if (showPlaceholder) {
    return (
      <div
        className={`${styles.teamLogo} ${styles.teamLogoPlaceholder} ${styles[size]} ${className}`}
        style={
          branding?.primaryColor
            ? { backgroundColor: branding.primaryColor }
            : {}
        }
      >
        {teamName ? teamName.charAt(0).toUpperCase() : "?"}
      </div>
    );
  }

  return (
    <div className={`${styles.teamLogo} ${styles[size]} ${className}`}>
      <img
        src={logoUrl}
        alt={`${teamName} logo`}
        className={styles.teamLogoImage}
        onError={handleImageError}
        onLoad={handleImageLoad}
        loading="lazy"
      />
    </div>
  );
};

export default TeamLogo;
