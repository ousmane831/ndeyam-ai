import clsx from 'clsx'
import { forwardRef, useId, type TextareaHTMLAttributes } from 'react'

export const TextareaField = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement> & { label: string; error?: string }>(
  function TextareaField({ label, error, id, rows = 3, className, ...props }, ref) {
    const autoId = useId()
    const fieldId = id ?? autoId
    return (
      <div className="space-y-1.5">
        <label htmlFor={fieldId} className="block text-sm font-medium text-slate-700">
          {label}
        </label>
        <textarea
          ref={ref}
          id={fieldId}
          rows={rows}
          aria-invalid={error ? true : undefined}
          className={clsx('block w-full rounded-lg border px-3 py-2 text-sm', error ? 'border-red-400' : 'border-slate-300', className)}
          {...props}
        />
        {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
      </div>
    )
  },
)
