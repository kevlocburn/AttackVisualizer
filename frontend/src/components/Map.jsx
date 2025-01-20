import React, { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet-ant-path";

const serverLocation = [40.8586, -74.1636]; 

const Map = ({ logs, highlightLog, highlightIndex }) => {
  const highlightedLine = useRef(null); 
  const mapRef = useRef(null); 
  const linesRef = useRef([]); 

  useEffect(() => {
    if (!mapRef.current) {

      const map = L.map("map", {
        minZoom: 2,
        dragging: true,
        zoomControl: true, 
        scrollWheelZoom: true, 
        doubleClickZoom: true,
        boxZoom: true,
        tap: true, 
      }).setView([20, 0], 2);

      mapRef.current = map;


      L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
        attribution: "© OpenStreetMap contributors © CARTO",
      }).addTo(map);

      // server marker
      L.circle(serverLocation, {
        color: "red",
        fillColor: "#ff4d4d",
        fillOpacity: 0.7,
        radius: 30000,
      }).addTo(map);

      // logs as markers and lines
      logs.forEach((log, index) => {
        const sourceLatLng = [log.latitude, log.longitude];

        // check correct coordinates
        if (
          sourceLatLng[0] !== null &&
          sourceLatLng[1] !== null &&
          !isNaN(sourceLatLng[0]) &&
          !isNaN(sourceLatLng[1])
        ) {
          const attackCount = log.attempts || 1;

          // attack marker
          const marker = L.circle(sourceLatLng, {
            color: "yellow",
            fillColor: "#ffff4d",
            fillOpacity: 0.8,
            radius: 30000 * Math.min(attackCount, 10), 
          }).addTo(map);

          // animated line connecting to the server
          const line = L.polyline.antPath([sourceLatLng, serverLocation], {
            delay: 300,
            color: "orange",
            weight: 3,
            opacity: 0.7,
            pulseColor: "#ffcc00",
          }).addTo(map);

          linesRef.current[index] = line; 

          // click events to highlight the log entry and line
          const onClick = () => {
            highlightLog(index); // highlight the log entry

            // Highlight the line
            if (highlightedLine.current) {
              // Reset the previous highlighted line
              highlightedLine.current.setStyle({
                color: "orange",
                weight: 3,
                opacity: 0.7,
              });
            }

            // highlighted line
            line.setStyle({
              color: "red",
              weight: 7,
              opacity: 1,
            });

            highlightedLine.current = line; 
          };

          marker.on("click", onClick);
          line.on("click", onClick);
        }
      });
    }

    // highlight the line corresponding to the selected log entry
    if (highlightIndex !== null && linesRef.current[highlightIndex]) {
      if (highlightedLine.current) {
        highlightedLine.current.setStyle({
          color: "orange",
          weight: 3,
          opacity: 0.7,
        });
      }

      const line = linesRef.current[highlightIndex];
      line.setStyle({
        color: "red",
        weight: 10,
        opacity: 1,
      });
      highlightedLine.current = line;
    }


    return () => {
      if (mapRef.current) {
        mapRef.current.remove(); 
        mapRef.current = null; 
      }
    };
  }, [logs, highlightLog, highlightIndex]); // Re-run the effect when logs or highlightIndex change

  return <div id="map" style={{ height: "100%", width: "100%" }}></div>;
};

export default Map;
