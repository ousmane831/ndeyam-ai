import { AxiosError, AxiosHeaders } from 'axios'
import { describe, expect, it } from 'vitest'
import { ApiError, toApiError } from './api'

function axiosError(status?: number, data?: unknown) {
  const config = { headers: new AxiosHeaders() }
  const response = status
    ? { status, data, statusText: '', headers: {}, config }
    : undefined
  return new AxiosError('fail', 'ERR', config, {}, response)
}

describe('toApiError', () => {
  it('signale une erreur réseau lorsque le serveur est injoignable', () => {
    const err = toApiError(axiosError())
    expect(err.code).toBe('network_error')
    expect(err.status).toBeNull()
  })

  it('reprend le message et les erreurs de champ renvoyés par le backend', () => {
    const err = toApiError(
      axiosError(400, { detail: 'Les données envoyées sont invalides.', code: 'validation_error', errors: { poids: ['Doit être positif.'] } }),
    )
    expect(err).toBeInstanceOf(ApiError)
    expect(err.message).toBe('Les données envoyées sont invalides.')
    expect(err.fieldErrors.poids).toEqual(['Doit être positif.'])
  })

  it('fournit un message par défaut pour une erreur 500 sans corps', () => {
    expect(toApiError(axiosError(500)).message).toMatch(/erreur interne/)
  })
})

describe('erreurs imbriquées', () => {
  it('aplatit les erreurs par ligne (ex. séance de pesée)', () => {
    const err = toApiError(axiosError(400, { detail: 'x', errors: { '1': { weight_kg: ['Le poids doit être supérieur à zéro.'] } } }))
    expect(err.fieldErrors['1']).toEqual(['Le poids doit être supérieur à zéro.'])
  })
})
