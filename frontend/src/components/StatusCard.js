import React from "react";
import "./StatusCard.css";

const StatusCard = ({ title, value, status = "info" }) => {
  return (
    <div className={`status-card status-card--${status}`}>
      <h3 className="status-card__title">{title}</h3>
      <p className="status-card__value">{value}</p>
    </div>
  );
};

export default StatusCard;
