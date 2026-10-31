import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';
import { fileURLToPath, URL } from 'node:url';

// Capacitor later: `npx cap init` + `npx cap add ios android` wraps the built `dist/` as-is.
export default defineConfig({
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'Seizure Diary',
        short_name: 'Diary',
        description: 'Voice seizure diary with a personal risk level, trigger lab and clinic report',
        theme_color: '#14233a',
        background_color: '#f6f7f9',
        display: 'standalone',
        icons: [{ src: 'icon.svg', sizes: 'any', type: 'image/svg+xml' }],
      },
    }),
  ],
  server: { proxy: { '/api': { target: process.env.VITE_API_TARGET || 'http://localhost:8000', changeOrigin: true, rewrite: (p) => p.replace(/^\/api/, '') } } },
});
