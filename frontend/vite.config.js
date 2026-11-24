import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: { port: 3000 },
  // chart.js + leaflet + react in one bundle is ~600 kB; fine for this app.
  build: { chunkSizeWarningLimit: 1000 },
});
