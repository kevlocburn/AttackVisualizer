import React, { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet-ant-path";

const serverLocation = [40.8586, -74.1636]; // Server location

const Map = ({ maplogs, highlightLog, highlightIndex }) => {
  const mapRef = useRef(null); // Reference to the map instance
  const linesRef = useRef([]); // Store lines for highlighting
  const markersRef = useRef([]); // Store markers for cleanup

  // Initialize the map only once
  useEffect(() => {
    if (!mapRef.current) {
      const map = L.map("map", {
        minZoom: 2,
        dragging: true,
        zoomControl: true,
        scrollWheelZoom: true,
        doubleClickZoom: true,
        boxZoom: true,
        tap: false, // Disable touch tap for better mobile performance
      }).setView([20, 0], 2);

      mapRef.current = map;

      // Add tile layer
      L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
        attribution: "© OpenStreetMap contributors © CARTO",
      }).addTo(map);

      // Add server marker
      L.circle(serverLocation, {
        color: "red",
        fillColor: "#ff4d4d",
        fillOpacity: 0.7,
        radius: 30000,
      }).addTo(map);
    }
  }, []);

  // Update markers and lines when `maplogs` changes
  useEffect(() => {
    const map = mapRef.current;

    if (!map) return;

    // Clear existing markers and lines
    markersRef.current.forEach((marker) => map.removeLayer(marker));
    linesRef.current.forEach((line) => map.removeLayer(line));
    markersRef.current = [];
    linesRef.current = [];

    // Add new markers and lines
    maplogs.forEach((log, index) => {
      const sourceLatLng = [log.latitude, log.longitude];

      if (
        sourceLatLng[0] !== null &&
        sourceLatLng[1] !== null &&
        !isNaN(sourceLatLng[0]) &&
        !isNaN(sourceLatLng[1])
      ) {
        // Add marker
        const attackCount = log.attempts || 1;
        const marker = L.circle(sourceLatLng, {
          color: "yellow",
          fillColor: "#ffff4d",
          fillOpacity: 0.8,
          radius: 30000 * Math.min(attackCount, 10),
        }).addTo(map);

        markersRef.current.push(marker);

        // Add line to the server
        const line = L.polyline.antPath([sourceLatLng, serverLocation], {
          delay: 300,
          color: "orange",
          weight: 3,
          opacity: 0.7,
          pulseColor: "#ffcc00",
          hardwareAccelerated: true, // Improve performance on mobile
        }).addTo(map);

        linesRef.current.push(line);

        // Add click event for highlighting
        marker.on("click", () => highlightLog(index));
        line.on("click", () => highlightLog(index));
      }
    });
  }, [maplogs, highlightLog]);

  // Highlight specific line when `highlightIndex` changes
  useEffect(() => {
    if (highlightIndex !== null && linesRef.current[highlightIndex]) {
      // Reset previous highlighted line
      linesRef.current.forEach((line, index) => {
        line.setStyle({
          color: index === highlightIndex ? "red" : "orange",
          weight: index === highlightIndex ? 7 : 3,
          opacity: index === highlightIndex ? 1 : 0.7,
        });
      });
    }
  }, [highlightIndex]);

  return <div id="map" style={{ height: "100%", width: "100%" }}></div>;
};

export default Map;
