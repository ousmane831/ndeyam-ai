/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'
import { readFileSync, writeFileSync } from 'node:fs'
import { defineConfig, loadEnv, type Plugin } from 'vite'

/**
 * Mode hors ligne : liste des fichiers de l'interface (préchargés par le service worker) et identifiant de
 * version inscrit dans sw.js, pour qu'une nouvelle version remplace l'ancienne sur les téléphones.
 */
function offlineAssets(): Plugin {
  let outDir = 'dist'
  let assets: string[] = []
  return {
    name: 'ndeyam-offline-assets',
    apply: 'build',
    configResolved(config) {
      outDir = config.build.outDir
    },
    generateBundle(_options, bundle) {
      assets = Object.keys(bundle).filter((f) => f.startsWith('assets/')).map((f) => `/${f}`).sort()
      this.emitFile({ type: 'asset', fileName: 'asset-list.json', source: JSON.stringify(assets) })
    },
    writeBundle() {
      const file = `${outDir}/sw.js`
      const buildId = Buffer.from(assets.join('|')).toString('base64url').slice(-16)
      writeFileSync(file, readFileSync(file, 'utf8').replace('__BUILD_ID__', buildId))
    },
  }
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendUrl = env.VITE_BACKEND_URL || 'http://localhost:8000'

  return {
    plugins: [react(), tailwindcss(), offlineAssets()],
    resolve: {
      alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
    },
    server: {
      port: 5173,
      // En développement, /api est relayé vers Django : pas de problème CORS côté navigateur.
      proxy: { '/api': { target: backendUrl, changeOrigin: true } },
    },
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: ['./src/test/setup.ts'],
      css: false,
    },
  }
})
