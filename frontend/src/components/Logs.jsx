import React, { useEffect, useState, useRef } from "react";
import "./Logs.css";

const Logs = ({ maplogs, highlightIndex, onLogClick }) => {
  const logRefs = useRef([]);

  useEffect(() => {
    // scroll to the highlighted log
    if (highlightIndex !== null && logRefs.current[highlightIndex]) {
      logRefs.current[highlightIndex].scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [highlightIndex]);

  // convert UTC timestamp to local time
  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp); // parse the UTC timestamp
    return date.toLocaleString(); // convert to local time
  };

  return (
    <div className="logs">
      <h2>Attack Logs</h2>
      <div className="log-list">
        {maplogs.map((log, index) => (
          <div
            key={index}
            ref={(el) => (logRefs.current[index] = el)} // save each log entry ref
            className={`log-entry ${highlightIndex === index ? "highlight" : ""}`} s
            onClick={() => onLogClick(index)} // highlight line on click
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
