import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it } from 'vitest'
import { Modal } from './Modal'

function ControlledModal() {
  const [text, setText] = useState('')
  // onClose inline : nouvelle fonction à chaque rendu (cas réel des pages).
  return (
    <Modal open title="Test" onClose={() => undefined}>
      <label htmlFor="champ">Champ</label>
      <input id="champ" value={text} onChange={(e) => setText(e.target.value)} />
    </Modal>
  )
}

describe('Modal', () => {
  it('ne vole pas le focus d’un champ contrôlé pendant la saisie', async () => {
    render(<ControlledModal />)
    await userEvent.type(screen.getByLabelText('Champ'), 'Saisie complète')
    expect(screen.getByLabelText('Champ')).toHaveValue('Saisie complète')
    expect(screen.getByLabelText('Champ')).toHaveFocus()
  })
})
