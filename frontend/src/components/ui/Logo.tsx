export function Logo({ className = 'size-9' }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden>
      <rect width="32" height="32" rx="7" fill="#1b4332" />
      <path d="M9 23c0-8 5-13 14-14-1 9-6 14-14 14Z" fill="#52b788" />
      <path d="M9 23 18 14" stroke="#1b4332" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  )
}
