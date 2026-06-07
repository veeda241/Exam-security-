import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import webExtension, { readJsonFile } from "vite-plugin-web-extension";

function generateManifest() {
  const manifest = readJsonFile("manifest.json");
  return manifest;
}

export default defineConfig({
  plugins: [
    react(),
    webExtension({
      manifest: generateManifest,
      watchMode: true,
    }),
  ],
  resolve: {
    alias: {
      "@": "/src",
    },
  },
});
