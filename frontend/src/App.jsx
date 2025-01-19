import React, { useState, useEffect } from "react";
import Map from "./components/Map";
import Logs from "./components/Logs";
import ChartSection from "./components/ChartSection";
import "./App.css";

function App() {
  const [logs, setLogs] = useState([]);
  const [highlightIndex, setHighlightIndex] = useState(null);

  useEffect(() => {
    // Fetch logs from the backend
    fetch("http://127.0.0.1:8000/logs/")
      .then((response) => response.json())
      .then((data) => setLogs(data))
      .catch((error) => console.error("Error fetching logs:", error));
  }, []);

  return (
    <div className="app">
      <div className="map-container">
        <Map logs={logs} highlightLog={setHighlightIndex} highlightIndex={highlightIndex} />
      </div>
      <div className="bottom-container">
        <div className="logs-section">
          <Logs logs={logs} highlightIndex={highlightIndex} onLogClick={setHighlightIndex} />
        </div>
        <div className="chart-section">
          <ChartSection logs={logs} />
        </div>
      </div>
    </div>
  );
}

export default App;
