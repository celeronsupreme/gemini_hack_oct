import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';
import { fileURLToPath, URL } from 'node:url';

// Android: `pnpm android:apk` builds with CAP_BUILD=1 and wraps `dist/` in `android/` (Capacitor). The WebView serves the
// bundle itself, so the service worker is left out of that build.
export default defineConfig({
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  plugins: [
    react(),
    VitePWA({
      disable: process.env.CAP_BUILD === '1',
      registerType: 'autoUpdate',
      manifest: {
        name: 'Seizure Diary',
        short_name: 'Diary',
        description: 'Voice seizure diary with a personal risk level, trigger lab and clinic report',
        theme_color: '#F2F2F7',
        background_color: '#f6f7f9',
        display: 'standalone',
        icons: [{ src: 'icon.svg', sizes: 'any', type: 'image/svg+xml' }],
      },
    }),
  ],
  // allowedHosts: ngrok tunnels (`ngrok http 5173`) for testing the Live session on a real phone over HTTPS.
  server: { allowedHosts: ['.ngrok-free.app', '.ngrok-free.dev', '.ngrok.app', '.ngrok.dev'], proxy: { '/api': { target: process.env.VITE_API_TARGET || 'http://localhost:8000', changeOrigin: true, rewrite: (p) => p.replace(/^\/api/, '') } } },
});
