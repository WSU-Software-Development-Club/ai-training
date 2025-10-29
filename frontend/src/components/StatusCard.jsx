import React from "react";
import styles from "../styles/components/StatusCard.module.css";

const StatusCard = ({ title, value, status = "info" }) => {
  const variantClass =
    status === "success"
      ? styles.statusCardSuccess
      : status === "warning"
      ? styles.statusCardWarning
      : status === "error"
      ? styles.statusCardError
      : styles.statusCardInfo;

  return (
    <div className={`${styles.statusCard} ${variantClass}`}>
      <h3 className={styles.statusCardTitle}>{title}</h3>
      <p className={styles.statusCardValue}>{value}</p>
    </div>
  );
};

export default StatusCard;
