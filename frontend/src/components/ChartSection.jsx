import React, { useEffect, useState } from "react";
import { Bar, Line, Radar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  BarElement,
  CategoryScale,
  LinearScale,
  Title,
  Tooltip,
  Legend,
  LineElement,
  PointElement,
  RadialLinearScale,
} from "chart.js";

ChartJS.register(
  BarElement,
  CategoryScale,
  LinearScale,
  Title,
  Tooltip,
  Legend,
  LineElement,
  PointElement,
  RadialLinearScale
);

const ChartSection = ({ logs }) => {
  const [topCountriesData, setTopCountriesData] = useState(null);
  const [attackTrendsData, setAttackTrendsData] = useState(null);
  const [timeOfDayData, setTimeOfDayData] = useState(null);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(max-width: 768px)");
    const handleMediaQueryChange = (e) => setIsMobile(e.matches);

    // Set initial value
    setIsMobile(mediaQuery.matches);

    // Add listener
    mediaQuery.addEventListener("change", handleMediaQueryChange);

    // Cleanup listener on unmount
    return () => mediaQuery.removeEventListener("change", handleMediaQueryChange);
  }, []);

  useEffect(() => {
    // "Top Attack Sources (Country)"
    const topCountries = logs.reduce((acc, log) => {
      const key = log.country || "Unknown";
      acc[key] = (acc[key] || 0) + 1;
      return acc;
    }, {});

    const topCountriesSorted = Object.entries(topCountries)
      .sort((a, b) => b[1] - a[1])
      .slice(0, isMobile ? 2 : 10);

    setTopCountriesData({
      labels: topCountriesSorted.map(([country]) => country),
      datasets: [
        {
          label: "Number of Attempts",
          data: topCountriesSorted.map(([_, count]) => count),
          backgroundColor: "rgba(255, 159, 64, 0.6)",
          borderColor: "rgba(255, 159, 64, 1)",
          borderWidth: 1,
        },
      ],
    });

    // "Attack Trends Over Time"
    const trends = logs.reduce((acc, log) => {
      const date = new Date(log.timestamp).toLocaleDateString();
      acc[date] = (acc[date] || 0) + 1;
      return acc;
    }, {});

    const trendsSorted = Object.entries(trends).sort(([a], [b]) => new Date(a) - new Date(b));

    setAttackTrendsData({
      labels: trendsSorted.map(([date]) => date),
      datasets: [
        {
          label: logs.country.count +" Attacks",
          data: trendsSorted.map(([_, count]) => count),
          fill: true,
          backgroundColor: "rgba(75, 192, 192, 0.2)",
          borderColor: "rgba(75, 192, 192, 1)",
        },
      ],
    });

    // "Attack Distribution by Time of Day"
    const hours = new Array(24).fill(0); // Array for 24 hours
    logs.forEach((log) => {
      const hour = new Date(log.timestamp).getHours(); // Extract hour
      hours[hour]++;
    });

    setTimeOfDayData({
      labels: Array.from({ length: 24 }, (_, i) => `${i}:00 - ${i + 1}:00`),
      datasets: [
        {
          label: "Number of Attacks",
          data: hours,
          backgroundColor: "rgba(153, 102, 255, 0.6)",
          borderColor: "rgba(153, 102, 255, 1)",
          borderWidth: 1,
        },
      ],
    });
  }, [logs, isMobile]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <div>
        <h3>Top Attack Sources (Country)</h3>
        {topCountriesData ? <Bar data={topCountriesData} options={{ responsive: true }} /> : <p>Loading...</p>}
      </div>
      <div>
        <h3>Attack Trends Over Time</h3>
        {attackTrendsData ? <Line data={attackTrendsData} options={{ responsive: true }} /> : <p>Loading...</p>}
      </div>
      <div>
        <h3>Attack Distribution by Time of Day</h3>
        {timeOfDayData ? <Bar data={timeOfDayData} options={{ responsive: true, indexAxis: "y" }} /> : <p>Loading...</p>}
      </div>
    </div>
  );
};

export default ChartSection;