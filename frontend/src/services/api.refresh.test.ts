import axios, { AxiosError, AxiosHeaders, type AxiosAdapter, type InternalAxiosRequestConfig } from 'axios'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { api, ApiError, onSessionExpired } from './api'
import { tokenStore } from './tokens'

/** Faux serveur : n'accepte que le jeton d'accès « nouveau ». */
const adapter: AxiosAdapter = async (config: InternalAxiosRequestConfig) => {
  const auth = AxiosHeaders.from(config.headers).get('Authorization')
  if (auth === 'Bearer nouveau') {
    return { data: { ok: true, url: config.url }, status: 200, statusText: 'OK', headers: {}, config }
  }
  const response = { data: { detail: 'Jeton expiré', code: 'token_not_valid' }, status: 401, statusText: '', headers: {}, config }
  throw new AxiosError('401', 'ERR_BAD_REQUEST', config, {}, response)
}

describe('renouvellement automatique du jeton', () => {
  const originalAdapter = api.defaults.adapter

  beforeEach(() => {
    api.defaults.adapter = adapter
    tokenStore.setTokens('ancien', 'refresh-valide', true)
  })

  afterEach(() => {
    api.defaults.adapter = originalAdapter
    tokenStore.clear()
    vi.restoreAllMocks()
  })

  it('renouvelle le jeton puis rejoue la requête', async () => {
    const post = vi.spyOn(axios, 'post').mockResolvedValue({ data: { access: 'nouveau', refresh: 'refresh-2' } })
    const { data } = await api.get('/auth/me/')
    expect(data.ok).toBe(true)
    expect(post).toHaveBeenCalledTimes(1)
    expect(tokenStore.getAccess()).toBe('nouveau')
    expect(tokenStore.getRefresh()).toBe('refresh-2')
  })

  it('mutualise le renouvellement entre requêtes simultanées', async () => {
    const post = vi.spyOn(axios, 'post').mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve({ data: { access: 'nouveau', refresh: 'refresh-2' } }), 10)),
    )
    const results = await Promise.all([api.get('/farms/'), api.get('/auth/me/'), api.get('/health/')])
    expect(results.every((r) => r.data.ok)).toBe(true)
    expect(post).toHaveBeenCalledTimes(1)
  })

  it('termine la session si le renouvellement échoue', async () => {
    vi.spyOn(axios, 'post').mockRejectedValue(new Error('refus'))
    const listener = vi.fn()
    const unsubscribe = onSessionExpired(listener)
    await expect(api.get('/auth/me/')).rejects.toMatchObject({ code: 'session_expired' })
    expect(listener).toHaveBeenCalledTimes(1)
    expect(tokenStore.getRefresh()).toBeNull()
    unsubscribe()
  })

  it('ne tente pas de renouvellement sur un échec de connexion', async () => {
    const post = vi.spyOn(axios, 'post')
    const error = await api.post('/auth/login/', {}).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(401)
    expect(post).not.toHaveBeenCalled()
  })
})
