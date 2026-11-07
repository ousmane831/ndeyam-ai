import { beforeEach, describe, expect, it } from 'vitest'
import { tokenStore } from './tokens'

describe('tokenStore', () => {
  beforeEach(() => {
    tokenStore.clear()
  })

  it("garde le jeton d'accès uniquement en mémoire", () => {
    tokenStore.setTokens('access-1', 'refresh-1', true)
    expect(tokenStore.getAccess()).toBe('access-1')
    expect(JSON.stringify(localStorage)).not.toContain('access-1')
    expect(JSON.stringify(sessionStorage)).not.toContain('access-1')
  })

  it('« Rester connecté » conserve le jeton de rafraîchissement dans localStorage', () => {
    tokenStore.setTokens('a', 'r-persistant', true)
    expect(localStorage.getItem('ndeyam.refresh')).toBe('r-persistant')
    expect(sessionStorage.getItem('ndeyam.refresh')).toBeNull()
  })

  it('sans « Rester connecté », le jeton est limité à la session du navigateur', () => {
    tokenStore.setTokens('a', 'r-session', false)
    expect(sessionStorage.getItem('ndeyam.refresh')).toBe('r-session')
    expect(localStorage.getItem('ndeyam.refresh')).toBeNull()
  })

  it('un renouvellement conserve le mode de stockage choisi à la connexion', () => {
    tokenStore.setTokens('a', 'r1', false)
    tokenStore.setTokens('b', 'r2')
    expect(sessionStorage.getItem('ndeyam.refresh')).toBe('r2')
    expect(localStorage.getItem('ndeyam.refresh')).toBeNull()
  })

  it('clear efface tout', () => {
    tokenStore.setTokens('a', 'r', true)
    tokenStore.clear()
    expect(tokenStore.getAccess()).toBeNull()
    expect(tokenStore.getRefresh()).toBeNull()
  })
})
