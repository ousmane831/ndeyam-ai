import clsx from 'clsx'
import { useTranslation } from 'react-i18next'
import { LANGUAGES, setLanguage } from '@/i18n'

/** Choix de la langue (FR / EN), mémorisé sur l'appareil. */
export function LanguageSwitcher({ tone = 'light' }: { tone?: 'light' | 'dark' }) {
  const { t, i18n } = useTranslation()
  return (
    <div role="group" aria-label={t('Langue')} className="inline-flex rounded-md p-0.5 ring-1 ring-inset ring-slate-300">
      {LANGUAGES.map((l) => {
        const on = i18n.language === l.code
        return (
          <button key={l.code} type="button" lang={l.code} aria-pressed={on} title={l.label} onClick={() => setLanguage(l.code)}
            className={clsx('min-h-9 min-w-10 rounded px-2 font-mono text-xs font-semibold',
              on ? 'bg-brand-800 text-white' : tone === 'dark' ? 'text-brand-100 hover:bg-brand-800' : 'text-slate-600 hover:bg-slate-100')}>
            <span aria-hidden>{l.short}</span><span className="sr-only">{l.label}</span>
          </button>
        )
      })}
    </div>
  )
}
