import clsx from 'clsx'

/**
 * Symbole NDEYAM : tête de bélier aux cornes enroulées (le Ladoum, emblème de l'élevage ovin
 * sénégalais), en indigo sur un carré couleur mil. Lisible de 16 px (favicon) à l'affiche.
 */
export function Logo({ className = 'size-9' }: { className?: string }) {
  return (
    <svg viewBox="0 0 56 56" className={className} aria-hidden>
      <rect width="56" height="56" rx="9" fill="#e0a72e" />
      <g fill="none" stroke="#1d2b53" strokeWidth="4.6" strokeLinecap="round" strokeLinejoin="round">
        <path d="M24.5 19.5C19 11 7 13 7.5 24c.4 8.5 10.5 9.5 11 3.5.3-4-5-4.5-5.5-1.5" />
        <path d="M31.5 19.5C37 11 49 13 48.5 24c-.4 8.5-10.5 9.5-11 3.5-.3-4 5-4.5 5.5-1.5" />
      </g>
      <path d="M21.5 20.5Q28 16.5 34.5 20.5L31.3 41.5Q28 46.5 24.7 41.5Z" fill="#1d2b53" />
    </svg>
  )
}

/** Logotype : symbole + « NDEYAM » (titre) + « AI » discret. `tone` selon le fond. */
export function Wordmark({ tone = 'dark', size = 'md' }: { tone?: 'dark' | 'light'; size?: 'md' | 'lg' }) {
  return (
    <span className="inline-flex items-center gap-3">
      <Logo className={size === 'lg' ? 'size-11' : 'size-9'} />
      <span className="flex items-baseline gap-1.5">
        <span
          className={clsx(
            'font-display font-extrabold tracking-[0.04em]',
            size === 'lg' ? 'text-2xl' : 'text-xl',
            tone === 'light' ? 'text-white' : 'text-brand-800',
          )}
        >
          NDEYAM
        </span>
        <span className={clsx('font-mono text-xs font-semibold', tone === 'light' ? 'text-mil-300' : 'text-mil-600')}>AI</span>
      </span>
    </span>
  )
}
