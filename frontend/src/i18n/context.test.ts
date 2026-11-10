import { describe, expect, it } from 'vitest'
import i18n from './index'

describe('langue de l’interface', () => {
  it('« Nom » d’une personne : « Last name » en anglais, inchangé en français', async () => {
    expect(i18n.t('Nom', { context: 'person' })).toBe('Nom')
    await i18n.changeLanguage('en')
    try {
      expect(i18n.t('Nom', { context: 'person' })).toBe('Last name')
      expect(i18n.t('Nom')).toBe('Name')
      expect(document.documentElement.lang).toBe('en')
    } finally {
      await i18n.changeLanguage('fr')
    }
  })
})
