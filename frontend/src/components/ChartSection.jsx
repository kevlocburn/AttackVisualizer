import React, { useEffect, useState } from "react";
import { Bar, Line } from "react-chartjs-2";
import { Chart as ChartJS, BarElement, CategoryScale, LinearScale, Title, Tooltip, Legend, LineElement, PointElement } from "chart.js";

ChartJS.register(
  BarElement,
  CategoryScale,
  LinearScale,
  Title,
  Tooltip,
  Legend,
  LineElement,
  PointElement
);

const ChartSection = ({ logs }) => {
  const [topCountriesData, setTopCountriesData] = useState(null);
  const [attackTrendsData, setAttackTrendsData] = useState(null);

  useEffect(() => {
    // data for "Top Attack Sources (Country)"
    const topCountries = logs.reduce((acc, log) => {
      const key = log.country || "Unknown";
      acc[key] = (acc[key] || 0) + 1;
      return acc;
    }, {});

    const topCountriesSorted = Object.entries(topCountries)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10); // top 10 countries

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

    // data for "Attack Trends"
    const trends = logs.reduce((acc, log) => {
      const date = new Date(log.timestamp).toLocaleDateString(); // group by date
      acc[date] = (acc[date] || 0) + 1;
      return acc;
    }, {});

    const trendsSorted = Object.entries(trends).sort(([a], [b]) => new Date(a) - new Date(b));

    setAttackTrendsData({
      labels: trendsSorted.map(([date]) => date),
      datasets: [
        {
          label: "Number of Attacks",
          data: trendsSorted.map(([_, count]) => count),
          fill: true,
          backgroundColor: "rgba(75, 192, 192, 0.2)",
          borderColor: "rgba(75, 192, 192, 1)",
        },
      ],
    });
  }, [logs]);

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
    </div>
  );
};

export default ChartSection;
