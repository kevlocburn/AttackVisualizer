import React from "react";
import "./Spinner.css";

const Spinner = ({ label = "Loading...", size = 36, inline = false }) => {
  const spinner = (
    <div
      className="spinner"
      style={{ width: size, height: size, borderWidth: Math.max(3, size / 9) }}
    />
  );

  if (inline) {
    return spinner;
  }

  return (
    <div className="spinner-container">
      {spinner}
      {label && <p className="spinner-label">{label}</p>}
    </div>
  );
};

export default Spinner;
