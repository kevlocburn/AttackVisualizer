import React, { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet-ant-path";

const serverLocation = [40.8586, -74.1636]; // Server location

const Map = ({ mapLogs, highlightLog, highlightIndex }) => {
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

      // Server marker
      L.circle(serverLocation, {
        color: "red",
        fillColor: "#ff4d4d",
        fillOpacity: 0.7,
        radius: 30000,
      }).addTo(map);

      // mapLogs as markers and lines
      mapLogs.forEach((log, index) => {
        const sourceLatLng = [log.latitude, log.longitude];

        if (sourceLatLng[0] !== null && sourceLatLng[1] !== null) {
          const attackCount = log.attempts || 1;

          const marker = L.circle(sourceLatLng, {
            color: "yellow",
            fillColor: "#ffff4d",
            fillOpacity: 0.8,
            radius: 30000 * Math.min(attackCount, 10), 
          }).addTo(map);

          const line = L.polyline.antPath([sourceLatLng, serverLocation], {
            delay: 300,
            color: "orange",
            weight: 3,
            opacity: 0.7,
            pulseColor: "#ffcc00",
          }).addTo(map);

          linesRef.current[index] = line;

          const onClick = () => {
            highlightLog(index);

            if (highlightedLine.current) {
              highlightedLine.current.setStyle({
                color: "orange",
                weight: 3,
                opacity: 0.7,
              });
            }

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
  }, [mapLogs, highlightLog, highlightIndex]);

  return <div id="map" style={{ height: "100%", width: "100%" }}></div>;
};

export default Map;
