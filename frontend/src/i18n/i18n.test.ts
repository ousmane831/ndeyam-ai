import { describe, expect, it } from 'vitest'
import { en } from './index'

const sources = import.meta.glob<string>(['../**/*.{ts,tsx}', '!../**/*.test.{ts,tsx}', '!../**/*.d.ts', '!../test/**'], { query: '?raw', import: 'default', eager: true })

/** Tous les textes passés à t('…') ou marqués tk('…') dans le code (hors tests), avec leur fichier. */
function keysInSource(): Map<string, string> {
  const found = new Map<string, string>()
  for (const [path, raw] of Object.entries(sources)) {
    // Les commentaires citent parfois t('…') : on ne les compte pas.
    const src = raw.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:'"])\/\/.*$/gm, '$1')
    const re = /\b(?:t|tk)\(\s*(['"])((?:\\.|(?!\1)[^\\])*)\1/g
    for (let m = re.exec(src); m; m = re.exec(src)) {
      const key = m[2].replace(/\\(['"\\])/g, '$1').replace(/\\n/g, '\n')
      if (!found.has(key)) found.set(key, path.replace('../', 'src/'))
    }
  }
  return found
}

const vars = (s: string) => [...s.matchAll(/\{\{\s*(\w+)\s*\}\}/g)].map((m) => m[1]).sort()

describe('traductions anglaises', () => {
  const keys = keysInSource()

  it('chaque texte de l’interface a sa traduction anglaise', () => {
    const missing = [...keys].filter(([k]) => !(k in en)).map(([k, f]) => `${f} : « ${k} »`)
    expect(missing, `${missing.length} texte(s) sans traduction :\n${missing.join('\n')}`).toEqual([])
  })

  it('les variables ({{…}}) sont les mêmes en français et en anglais', () => {
    const wrong = Object.entries(en).filter(([k, v]) => vars(k).join() !== vars(v).join()).map(([k, v]) => `« ${k} » → « ${v} »`)
    expect(wrong).toEqual([])
  })

  it('aucune traduction vide', () => {
    expect(Object.entries(en).filter(([, v]) => !v.trim()).map(([k]) => k)).toEqual([])
  })

  it('l’interface est réellement traduite (contrôle de volume)', () => {
    expect(keys.size).toBeGreaterThan(1000)
  })
})
