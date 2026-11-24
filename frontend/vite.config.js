import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: { port: 3000 },
  // chart.js + leaflet + react in one bundle is ~600 kB; fine for this app.
  build: {
    // Cloudflare's WAF on hack.kevinlockburner.com only allows a fixed set of
    // paths, including /static/ (where CRA put assets). Keep assets there.
    assetsDir: 'static',
    chunkSizeWarningLimit: 1000,
  },
});
