/** Enregistre le service worker en production uniquement (en développement, il gênerait le rechargement à chaud). */
export function registerServiceWorker() {
  if (!import.meta.env.PROD || !('serviceWorker' in navigator)) return
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {
      /* sans service worker, l'application fonctionne normalement */
    })
  })
}
