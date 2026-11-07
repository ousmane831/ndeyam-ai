import { api } from './api'

/** Télécharge un fichier protégé (export CSV) en conservant l'authentification et les filtres. */
export async function downloadFile(url: string, params: Record<string, unknown>, fallbackName: string) {
  const response = await api.get<Blob>(url, { params, responseType: 'blob' })
  const disposition = String(response.headers['content-disposition'] ?? '')
  const match = /filename="?([^";]+)"?/.exec(disposition)
  const href = URL.createObjectURL(response.data)
  const link = document.createElement('a')
  link.href = href
  link.download = match?.[1] ?? fallbackName
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(href)
}

/** Supprime les paramètres vides avant l'appel à l'API. */
export function cleanParams<T extends object>(params: T): Partial<T> {
  return Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v !== null && v !== undefined)) as Partial<T>
}
