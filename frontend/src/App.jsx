import React, { useState, useEffect } from "react";
import Map from "./components/Map";
import Logs from "./components/Logs";
import ChartSection from "./components/ChartSection";
import "./App.css";

function App() {
  const [logs, setLogs] = useState([]);
  const [mapLogs, setMapLogs] = useState([]);
  const [highlightIndex, setHighlightIndex] = useState(null);

  const API_BASE_URL =
    process.env.NODE_ENV === "production"
      ? "https://hack.kevinlockburner.com/api" // Production API URL
      : "http://127.0.0.1:8000"; // Local development API URL

  useEffect(() => {
    // Fetch logs for the log and chart sections
    fetch(`${API_BASE_URL}/logs/`)
      .then((response) => response.json())
      .then((data) => setLogs(data))
      .catch((error) => console.error("Error fetching logs:", error));

    // Fetch map logs for the map component
    fetch(`${API_BASE_URL}/maplogs/`)
      .then((response) => response.json())
      .then((data) => setMapLogs(data))
      .catch((error) => console.error("Error fetching map logs:", error));
  }, [API_BASE_URL]);

  return (
    <div className="app">
      <div className="map-container">
        <Map logs={mapLogs} highlightLog={setHighlightIndex} highlightIndex={highlightIndex} />
      </div>
      <div className="bottom-container">
        <div className="logs-section">
          <Logs logs={mapLogs} highlightIndex={highlightIndex} onLogClick={setHighlightIndex} />
        </div>
        <div className="chart-section">
          <ChartSection logs={logs} />
        </div>
      </div>
    </div>
  );
}

export default App;
