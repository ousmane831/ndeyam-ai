import clsx from 'clsx'
import { CheckCircle2, Minus, Plus, Printer, TriangleAlert, XCircle } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { Formula } from '@/types/formula'
import { formatMoney } from '@/utils/format'
import { IngredientIcon } from './IngredientIcon'
import { plainName, practicalQuantity, verdictOf } from './rationText'

const VERDICT_STYLE = {
  ok: { box: 'bg-acacia-50 text-acacia-800 border-acacia-200', icon: CheckCircle2 },
  wait: { box: 'bg-mil-50 text-mil-700 border-mil-200', icon: TriangleAlert },
  stop: { box: 'bg-red-50 text-red-800 border-red-200', icon: XCircle },
}

/**
 * Carte ration : l'essentiel en gros (combien donner par jour, combien ça coûte), pour tout le lot,
 * avec un pictogramme par aliment. Partage WhatsApp et impression. Les chiffres viennent de la formule ;
 * seuls l'arrondi d'affichage et la multiplication par le nombre d'animaux sont faits ici.
 */
export function RationCard({ formula }: { formula: Formula }) {
  const { t } = useTranslation()
  const lotSize = Number(formula.result_snapshot.profile?.head_count) || 1
  const [count, setCount] = useState(lotSize)
  const items = formula.items.filter((i) => i.quantity_as_fed_kg !== null && Number(i.quantity_as_fed_kg) > 0)
  if (items.length === 0) return null

  const perDay = (kg: string | null) => Number(kg ?? 0) * count
  const totalKg = items.reduce((s, i) => s + perDay(i.quantity_as_fed_kg), 0)
  const costPerAnimal = formula.cost_per_day !== null ? Number(formula.cost_per_day) : null
  const costPerDay = costPerAnimal !== null ? costPerAnimal * count : null
  const verdict = verdictOf(formula)
  const V = VERDICT_STYLE[verdict.tone]
  const animals = count > 1 ? t('{{count}} animaux', { count }) : t('1 animal')

  const shareText = [
    t('Ration « {{name}} » (Ndeyam AI)', { name: formula.name }),
    t('Pour {{animals}}, chaque jour :', { animals }),
    ...items.map((i) => t('- {{ingredient}} : {{quantity}}', { ingredient: plainName(i.ingredient_name), quantity: practicalQuantity(perDay(i.quantity_as_fed_kg)) })),
    costPerDay !== null
      ? t('Total : {{quantity}} par jour, {{cost}} par jour ({{costPerAnimal}} par animal).', {
          quantity: practicalQuantity(totalKg), cost: formatMoney(costPerDay, formula.currency), costPerAnimal: formatMoney(costPerAnimal, formula.currency),
        })
      : t('Total : {{quantity}} par jour.', { quantity: practicalQuantity(totalKg) }),
    verdict.share,
  ].join('\n')

  const print = () => {
    document.documentElement.classList.add('print-ration')
    window.addEventListener('afterprint', () => document.documentElement.classList.remove('print-ration'), { once: true })
    window.print()
  }

  return (
    <section aria-labelledby="ration-card-title" className="ration-card overflow-hidden rounded-md border border-slate-200 bg-white">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
        <div>
          <h2 id="ration-card-title" className="font-display text-xl font-bold text-brand-900">{t('À donner chaque jour')}</h2>
          <p className="text-sm text-slate-500">{formula.name}</p>
        </div>
        <div className="flex items-center gap-2" role="group" aria-label={t("Nombre d'animaux nourris")}>
          <span className="text-sm text-slate-600">{t('Pour')}</span>
          <button type="button" onClick={() => setCount((c) => Math.max(1, c - 1))} aria-label={t('Un animal de moins')}
            className="no-print inline-flex size-10 items-center justify-center rounded-md ring-1 ring-slate-300 ring-inset hover:bg-slate-50"><Minus className="size-4" /></button>
          <input aria-label={t("Nombre d'animaux")} inputMode="numeric" value={count}
            onChange={(e) => setCount(Math.max(1, Math.min(9999, Number(e.target.value.replace(/\D/g, '')) || 1)))}
            className="h-10 w-16 rounded-md border border-slate-300 text-center font-display text-lg font-bold tabular-nums" />
          <button type="button" onClick={() => setCount((c) => Math.min(9999, c + 1))} aria-label={t('Un animal de plus')}
            className="no-print inline-flex size-10 items-center justify-center rounded-md ring-1 ring-slate-300 ring-inset hover:bg-slate-50"><Plus className="size-4" /></button>
          <span className="text-sm text-slate-600">{count > 1 ? t('animaux') : t('animal')}</span>
        </div>
      </header>

      <ul className="divide-y divide-slate-100">
        {items.map((i) => (
          <li key={i.id} className="flex items-center gap-4 px-5 py-3">
            <IngredientIcon category={i.ingredient_category} size="lg" />
            <span className="min-w-0 flex-1 text-base font-medium text-slate-800">{plainName(i.ingredient_name)}</span>
            <span className="font-display text-2xl font-bold whitespace-nowrap text-brand-900 tabular-nums sm:text-3xl">{practicalQuantity(perDay(i.quantity_as_fed_kg))}</span>
          </li>
        ))}
      </ul>

      <div className="grid grid-cols-2 gap-px border-t border-slate-200 bg-slate-200">
        <div className="bg-brand-900 px-5 py-4 text-white">
          <p className="text-sm text-brand-100">{t('Total par jour')}</p>
          <p className="font-display text-2xl font-bold whitespace-nowrap tabular-nums sm:text-3xl">{practicalQuantity(totalKg)}</p>
        </div>
        <div className="bg-brand-900 px-5 py-4 text-white">
          <p className="text-sm text-brand-100">{t('Coût par jour')}</p>
          <p className="font-display text-2xl font-bold whitespace-nowrap tabular-nums sm:text-3xl">{costPerDay !== null ? formatMoney(costPerDay, formula.currency) : t('Inconnu')}</p>
        </div>
      </div>
      {costPerAnimal !== null && (
        <p className="px-5 pt-3 text-sm text-slate-600">
          {t("Soit {{costPerAnimal}} par animal et par jour ; {{costPerWeek}} pour une semaine ({{quantity}} d'aliment).", {
            costPerAnimal: formatMoney(costPerAnimal, formula.currency), costPerWeek: formatMoney(costPerDay! * 7, formula.currency), quantity: practicalQuantity(totalKg * 7),
          })}
        </p>
      )}

      <p className={clsx('mx-5 mt-3 flex items-start gap-2 rounded-md border px-3 py-2 text-sm font-medium', V.box)}>
        <V.icon className="mt-0.5 size-4 shrink-0" aria-hidden /> {verdict.text}
      </p>

      <div className="no-print flex flex-wrap gap-2 px-5 py-4">
        <a href={`https://wa.me/?text=${encodeURIComponent(shareText)}`} target="_blank" rel="noreferrer"
          className="inline-flex min-h-11 items-center gap-2 rounded-md bg-[#1f7a4d] px-4 text-sm font-semibold text-white hover:bg-[#186640]">
          <svg viewBox="0 0 24 24" className="size-4" aria-hidden fill="currentColor"><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2Zm0 18.2c-1.5 0-3-.4-4.2-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2Zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8-.2-.1-.4-.1-.6.1l-.8 1c-.1.2-.3.2-.5.1a6.7 6.7 0 0 1-3.3-2.9c-.3-.4.2-.4.7-1.4.1-.2 0-.3 0-.4l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5c-.2 0-.4.1-.6.3-.2.2-.8.8-.8 2s.8 2.3.9 2.5c.1.2 1.6 2.5 4 3.5 1.5.6 2 .7 2.8.6.4-.1 1.4-.6 1.6-1.1.2-.5.2-1 .1-1.1l-.5-.2Z" /></svg>
          {t('Partager sur WhatsApp')}
        </a>
        <button type="button" onClick={print}
          className="inline-flex min-h-11 items-center gap-2 rounded-md px-4 text-sm font-semibold text-brand-800 ring-1 ring-brand-300 ring-inset hover:bg-brand-50">
          <Printer className="size-4" aria-hidden /> {t('Imprimer la fiche')}
        </button>
      </div>
    </section>
  )
}
