import React from "react";
import styles from "../styles/components/GameTabs.module.css";

// Dumb placeholder for the live view. Takes `gameId` for parity with the other
// panels; it will consume it once the data layer lands.
const LivePanel = ({ gameId }) => (
  <div className={styles.panel}>
    <p className={styles.panelPlaceholder}>Live data goes here</p>
  </div>
);

export default LivePanel;
