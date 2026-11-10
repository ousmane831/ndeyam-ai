import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/services/api'
import { weighingService } from '@/services/animals'
import { formulaService } from '@/services/formulas'
import rawPack from './demo-pack.fixture.json'
import { estimateForGroup, matchReference } from './estimate'
import { linkOfflineResult, resetOfflineResultsCache } from './offlineResults'
import { outbox, setOutboxUser, syncOutbox } from './outbox'
import type { OfflinePack } from './pack'

const pack = rawPack as unknown as OfflinePack
const lot = (name: string) => pack.groups.find((g) => g.name === name)!
const objective = { entretien: 1, tabaski: 4 }
const session = { weighed_on: '2026-11-10', method: 'SCALE' as const, entries: [{ animal: 1, weight_kg: '18.9' }] }

describe('choix de la référence hors ligne (même règle que le serveur)', () => {
  it("retient la référence d'embouche pour le lot Tabaski avec l'objectif Tabaski", () => {
    expect(matchReference(pack.references, { ...lot('Embouche Tabaski'), objective: objective.tabaski })?.name).toMatch(/Mouton d'embouche/)
  })
  it("n'applique jamais une référence propre à un objectif sans cet objectif", () => {
    expect(matchReference(pack.references, { ...lot('Embouche Tabaski'), objective: null })).toBeNull()
  })
  it('refuse proprement un lot sans référence (agneaux)', () => {
    const est = estimateForGroup(pack, lot('Agneaux 2026').id, null, pack.ingredients.map((i) => i.id))!
    expect(est.result.status).toBe('REFUSED')
    expect(est.result.refusal_reasons[0]).toMatch(/Aucune référence DEMO/)
  })
  it('estime une ration DEMO avec les notes du lot et de la référence', () => {
    const est = estimateForGroup(pack, lot('Embouche Tabaski').id, objective.tabaski, pack.ingredients.map((i) => i.id))!
    expect(est.result.status).toBe('ESTIMATED')
    expect(est.result.items.length).toBeGreaterThan(0)
    expect(est.notes.join(' ')).toMatch(/Poids moyen du lot/)
    expect(est.notes.join(' ')).toMatch(/Référence retenue automatiquement/)
  })
})

describe("file d'envoi des saisies hors ligne", () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
    setOutboxUser(null)
    setOutboxUser(7)
  })
  afterEach(() => setOutboxUser(null))

  it('garde les saisies sur l’appareil, rattachées à l’utilisateur', () => {
    outbox.add({ kind: 'weighing-session', payload: session, label: 'Séance' })
    expect(JSON.parse(localStorage.getItem('ndeyam.outbox.7')!)).toHaveLength(1)
    setOutboxUser(8)
    expect(outbox.list()).toHaveLength(0) // un autre utilisateur ne voit pas (et n'envoie pas) ces saisies
    setOutboxUser(7)
    expect(outbox.list()).toHaveLength(1)
  })

  it("envoie dans l'ordre, s'arrête sur une coupure et garde les refus avec leur message", async () => {
    const bulk = vi.spyOn(weighingService, 'bulk')
      .mockResolvedValueOnce([])
      .mockRejectedValueOnce(new ApiError('Déjà pesé ce jour-là.', 400, 'invalid', { 0: ['Une pesée existe déjà.'] }))
      .mockRejectedValueOnce(new ApiError('Impossible de joindre le serveur.', null, 'network_error'))
    for (const label of ['A', 'B', 'C', 'D']) outbox.add({ kind: 'weighing-session', payload: session, label })
    expect(await syncOutbox()).toEqual({ sent: 1, failed: 1 })
    expect(bulk).toHaveBeenCalledTimes(3) // D n'est pas tenté après la coupure
    expect(outbox.list().map((e) => [e.label, e.error ?? null])).toEqual([
      ['B', 'Déjà pesé ce jour-là. Une pesée existe déjà.'], ['C', null], ['D', null],
    ])
  })

  it('relie le calcul hors ligne à la formule officielle enregistrée par le serveur', async () => {
    resetOfflineResultsCache()
    localStorage.setItem('ndeyam.refresh', 'x') // « Rester connecté » : résultats gardés dans localStorage
    vi.spyOn(formulaService, 'calculate').mockResolvedValue({ formula: { id: 42 } } as never)
    localStorage.setItem('ndeyam.offline-results', JSON.stringify([{ id: 'local-1', name: 'R', result: {} }]))
    outbox.add({ kind: 'formula', payload: { farm: 1, name: 'R', mode: 'ECONOMIC', group: 3, ingredients: [] }, label: 'Calcul', localResultId: 'local-1' })
    await syncOutbox()
    expect(JSON.parse(localStorage.getItem('ndeyam.offline-results')!)[0].serverFormulaId).toBe(42)
    linkOfflineResult('absent', 1) // sans effet sur un calcul inconnu
  })
})
