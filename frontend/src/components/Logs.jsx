import React, { useEffect, useRef } from "react";
import "./Logs.css";

const Logs = ({ mapLogs, highlightIndex, onLogClick }) => {
  const logRefs = useRef([]);

  useEffect(() => {
    if (highlightIndex !== null && logRefs.current[highlightIndex]) {
      logRefs.current[highlightIndex].scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [highlightIndex]);

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  return (
    <div className="logs">
      <h2>Attack Logs</h2>
      <div className="log-list">
        {mapLogs.map((log, index) => (
          <div
            key={index}
            ref={(el) => (logRefs.current[index] = el)}
            className={`log-entry ${highlightIndex === index ? "highlight" : ""}`}
            onClick={() => onLogClick(index)}
          >
            <p>
              <strong>IP:</strong> {log.ip_address}
            </p>
            <p>
              <strong>Time:</strong> {formatTimestamp(log.timestamp)}
            </p>
            <p>
              <strong>Location:</strong> {log.city || "Unknown"}, {log.region || "Unknown"}, {log.country || "Unknown"}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Logs;
