import React, { useState, useEffect } from "react";
import LoadingSpinner from "../components/LoadingSpinner"; // spinner component

export default function SpinnerTest() {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setLoading(false);
    }, 3000); // 3 second load (testing purposes)

    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="spinner-test-page">
      <h1>Spinner Test</h1>
      {loading ? <LoadingSpinner /> : <p>finished loading.</p>}
    </div>
  );
}
