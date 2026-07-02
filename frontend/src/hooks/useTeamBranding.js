import { useState, useEffect } from "react";
import { getTeamBranding, getTeamBrandingSync } from "../branding/teamBranding";

/**
 * React hook to get team branding data
 * @param {string} teamName - The team name to look up
 * @returns {Object} { branding, loading, error }
 */
export function useTeamBranding(teamName) {
  // Seed from the synchronous cache when available so the component paints with
  // the correct colors on first render (no flash of fallback styling). Falls
  // back to null when the team data hasn't been preloaded yet.
  const [branding, setBranding] = useState(() => getTeamBrandingSync(teamName));
  const [loading, setLoading] = useState(() => !getTeamBrandingSync(teamName));
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!teamName) {
      setBranding(null);
      setLoading(false);
      setError(null);
      return;
    }

    // If cached data is already available, use it synchronously and skip the
    // async fetch entirely.
    const syncBranding = getTeamBrandingSync(teamName);
    if (syncBranding) {
      setBranding(syncBranding);
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
