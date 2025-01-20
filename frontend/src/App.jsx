import React, { useState, useEffect } from "react";
import Map from "./components/Map";
import Logs from "./components/Logs";
import ChartSection from "./components/ChartSection";
import "./App.css";

function App() {
  const [logs, setLogs] = useState([]);
  const [maplogs, setMapLogs] = useState([]);
  const [highlightIndex, setHighlightIndex] = useState(null);

  const API_BASE_URL =
    process.env.NODE_ENV === "production"
      ? "https://hack.kevinlockburner.com/api" // Production API URL
      : "http://127.0.0.1:8000"; // Local development API URL

  useEffect(() => {
    // Fetch initial logs
    fetch(`${API_BASE_URL}/logs/`)
      .then((response) => response.json())
      .then((data) => setLogs(data))
      .catch((error) => console.error("Error fetching logs:", error));

    // Fetch initial map logs
    fetch(`${API_BASE_URL}/maplogs/`)
      .then((response) => response.json())
      .then((data) => setMapLogs(data))
      .catch((error) => console.error("Error fetching map logs:", error));

    // Connect to WebSocket for real-time updates
    const ws = new WebSocket(
      process.env.NODE_ENV === "production"
        ? "wss://hack.kevinlockburner.com/ws/logs"
        : "ws://127.0.0.1:8000/ws/logs"
    );

    ws.onmessage = (event) => {
      const newLog = JSON.parse(event.data);

      // Update state with the new log
      setLogs((prevLogs) => [newLog, ...prevLogs].slice(0, 100)); // Limit to 100 logs
      setMapLogs((prevMapLogs) => [newLog, ...prevMapLogs].slice(0, 100)); // Limit to 100 logs
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    ws.onclose = () => {
      console.log("WebSocket connection closed.");
    };

    return () => {
      ws.close();
    };
  }, [API_BASE_URL]);

  return (
    <div className="app">
      <div className="map-container">
        <Map maplogs={maplogs} highlightLog={setHighlightIndex} highlightIndex={highlightIndex} />
      </div>
      <div className="bottom-container">
        <div className="logs-section">
          <Logs maplogs={maplogs} highlightIndex={highlightIndex} onLogClick={setHighlightIndex} />
        </div>
        <div className="chart-section">
          <ChartSection logs={logs} />
        </div>
      </div>
    </div>
  );
}

export default App;
