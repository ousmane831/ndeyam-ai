import type { FieldValues, Path, UseFormSetError } from 'react-hook-form'
import { t } from '@/i18n'
import { ApiError } from '@/services/api'

/**
 * Reporte les erreurs de validation du backend sur les champs du formulaire.
 * Retourne le message général à afficher (ou null si tout a été rattaché à un champ).
 */
export function applyServerErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  knownFields: readonly Path<T>[],
): string | null {
  if (!(error instanceof ApiError)) return t('Une erreur inattendue est survenue.')
  const unmatched: string[] = []
  for (const [field, messages] of Object.entries(error.fieldErrors)) {
    if ((knownFields as readonly string[]).includes(field)) {
      setError(field as Path<T>, { type: 'server', message: messages.join(' ') })
    } else {
      unmatched.push(...messages)
    }
  }
  if (Object.keys(error.fieldErrors).length === 0) return error.message
  return unmatched.length ? unmatched.join(' ') : null
}
