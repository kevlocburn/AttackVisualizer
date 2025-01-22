import React, { useEffect, useState } from "react";
import { Bar, Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  BarElement,
  CategoryScale,
  LinearScale,
  Title,
  Tooltip,
  Legend,
  LineElement,
  PointElement, // Ensure this is registered
} from "chart.js";

ChartJS.register(
  BarElement,
  CategoryScale,
  LinearScale,
  Title,
  Tooltip,
  Legend,
  LineElement,
  PointElement // Explicitly register PointElement
);

const ChartSection = ({ apiBaseUrl }) => {
  const [topCountriesData, setTopCountriesData] = useState(null);
  const [attackTrendsData, setAttackTrendsData] = useState(null);
  const [timeOfDayData, setTimeOfDayData] = useState(null);
  const [totalFailedLogins, setTotalFailedLogins] = useState(null);

  useEffect(() => {
    // Fetch top attack sources
    fetch(`${apiBaseUrl}/charts/top-countries/`)
      .then((response) => response.json())
      .then((data) => {
        const labels = data.map((item) => item.country);
        const counts = data.map((item) => item.count);
        setTopCountriesData({
          labels,
          datasets: [
            {
              label: "Number of Attempts",
              data: counts,
              backgroundColor: "rgba(255, 159, 64, 0.6)",
              borderColor: "rgba(255, 159, 64, 1)",
              borderWidth: 1,
            },
          ],
        });
      })
      .catch((error) => console.error("Error fetching top countries:", error));

    // Fetch attack trends
    fetch(`${apiBaseUrl}/charts/attack-trends/`)
      .then((response) => response.json())
      .then((data) => {
        const labels = data.map((item) => item.date);
        const counts = data.map((item) => item.count);
        setAttackTrendsData({
          labels,
          datasets: [
            {
              label: "Attacks",
              data: counts,
              fill: true,
              backgroundColor: "rgba(75, 192, 192, 0.2)",
              borderColor: "rgba(75, 192, 192, 1)",
            },
          ],
        });
      })
      .catch((error) => console.error("Error fetching attack trends:", error));

    // Fetch time of day distribution
    fetch(`${apiBaseUrl}/charts/time-of-day/`)
      .then((response) => response.json())
      .then((data) => {
        const labels = data.map((item) => item.hour);
        const counts = data.map((item) => item.count);
        setTimeOfDayData({
          labels,
          datasets: [
            {
              label: "Number of Attacks",
              data: counts,
              backgroundColor: "rgba(153, 102, 255, 0.6)",
              borderColor: "rgba(153, 102, 255, 1)",
              borderWidth: 1,
            },
          ],
        });
      })
      .catch((error) => console.error("Error fetching time of day:", error));

    fetch(`${apiBaseUrl}/logs/counts/`)
      .then((response) => response.json())
      .then((data) => {
        setTotalFailedLogins(data.count)
      })
      .catch((error) => console.error("Error fetching total failed logins:", error));
  }, [apiBaseUrl]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <div>
        <h2>Total Failed Logins: {totalFailedLogins}</h2>
      </div>
      <div>
        <h3>Top Attack Sources (Country)</h3>
        {topCountriesData ? (
          <Bar data={topCountriesData} options={{ responsive: true }} />
        ) : (
          <p>Loading...</p>
        )}
      </div>
      <div>
        <h3>Attack Trends Over Time</h3>
        {attackTrendsData ? (
          <Line data={attackTrendsData} options={{ responsive: true }} />
        ) : (
          <p>Loading...</p>
        )}
      </div>
      <div>
        <h3>Attack Distribution by Time of Day</h3>
        {timeOfDayData ? (
          <Bar
            data={timeOfDayData}
            options={{ responsive: true, indexAxis: "y" }}
          />
        ) : (
          <p>Loading...</p>
        )}
      </div>
    </div>
  );
};

export default ChartSection;
