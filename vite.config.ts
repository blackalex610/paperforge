import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// The demo lives in web/; the Python functions in api/ are served locally by
// scripts/dev_server.py and by Vercel in production.
export default defineConfig({
  root: 'web',
  plugins: [react()],
  // KaTeX is most of the bundle and is needed on first paint anyway.
  build: { outDir: '../dist', emptyOutDir: true, chunkSizeWarningLimit: 600 },
  server: { proxy: { '/api': 'http://127.0.0.1:8787' } },
});
