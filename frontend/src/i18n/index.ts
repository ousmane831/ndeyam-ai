/**
 * Langues de l'interface : français (langue source) et anglais.
 *
 * Convention : la CLÉ d'une traduction est le texte français lui-même, `t('Mes animaux')`. Le français n'a donc
 * pas de fichier : un texte sans traduction s'affiche en français, jamais vide. Les traductions anglaises sont
 * rangées par domaine dans `src/locales/en/*.json` (fusionnés ici) ; le test `i18n.test.ts` vérifie que chaque
 * texte passé à `t()` a sa traduction. Ajouter une langue (wolof, pulaar…) = ajouter un dossier `locales/<code>/`.
 */
import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

export const LANGUAGES = [
  { code: 'fr', label: 'Français', short: 'FR', locale: 'fr-FR' },
  { code: 'en', label: 'English', short: 'EN', locale: 'en-GB' },
] as const
export type Language = (typeof LANGUAGES)[number]['code']

const STORAGE_KEY = 'ndeyam.lang'
const files = import.meta.glob<{ default: Record<string, string> }>('../locales/en/*.json', { eager: true })
export const en: Record<string, string> = Object.assign({}, ...Object.values(files).map((m) => m.default))

function initialLanguage(): Language {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'fr' || saved === 'en') return saved
  } catch {
    /* stockage indisponible */
  }
  if (import.meta.env.MODE === 'test') return 'fr'
  return typeof navigator !== 'undefined' && navigator.language?.toLowerCase().startsWith('en') ? 'en' : 'fr'
}

void i18n.use(initReactI18next).init({
  resources: { fr: { translation: {} }, en: { translation: en } },
  lng: initialLanguage(),
  fallbackLng: false,
  keySeparator: false,
  nsSeparator: false,
  returnEmptyString: false,
  interpolation: { escapeValue: false },
  react: { useSuspense: false },
})

const syncDocument = (lng: string) => {
  if (typeof document !== 'undefined') document.documentElement.lang = lng
}
syncDocument(i18n.language)
i18n.on('languageChanged', syncDocument)

export function setLanguage(lng: Language) {
  try {
    localStorage.setItem(STORAGE_KEY, lng)
  } catch {
    /* le choix reste valable pour la session */
  }
  void i18n.changeLanguage(lng)
}

export const currentLanguage = (): Language => (i18n.language === 'en' ? 'en' : 'fr')
/** Paramètres régionaux pour les dates et les nombres (en-GB : jour/mois/année, comme en Afrique de l'Ouest). */
export const currentLocale = () => LANGUAGES.find((l) => l.code === currentLanguage())!.locale

/**
 * Marque un texte à traduire déclaré hors d'un composant (listes de menus, options, constantes) : renvoie le
 * texte tel quel ; on le traduit à l'affichage avec `t(valeur)`. Le test de complétude repère `tk('…')`.
 */
export const tk = (key: string) => key

/** Pour le code hors composants React (formatage, messages construits dans des fonctions). */
export const t = (key: string, options?: Record<string, unknown>) => i18n.t(key, options) as string

export default i18n
