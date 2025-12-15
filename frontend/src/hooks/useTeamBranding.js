import { useState, useEffect } from "react";
import { getTeamBranding } from "../branding/teamBranding";

/**
 * React hook to get team branding data
 * @param {string} teamName - The team name to look up
 * @returns {Object} { branding, loading, error }
 */
export function useTeamBranding(teamName) {
  const [branding, setBranding] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!teamName) {
      setBranding(null);
      setLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;

    const fetchBranding = async () => {
      setLoading(true);
      setError(null);

      try {
        const data = await getTeamBranding(teamName);
        if (!cancelled) {
          setBranding(data);
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          console.error("Error fetching team branding:", err);
          setError(err.message || "Failed to load team branding");
          setBranding(null);
          setLoading(false);
        }
      }
    };

    fetchBranding();

    return () => {
      cancelled = true;
    };
  }, [teamName]);

  return { branding, loading, error };
}
