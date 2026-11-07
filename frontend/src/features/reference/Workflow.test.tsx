import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { WorkflowActions } from './Workflow'

describe('WorkflowActions', () => {
  it('un éleveur ne peut que soumettre', () => {
    render(<WorkflowActions status="DRAFT" canSubmit isReviewer={false} onAction={vi.fn()} />)
    expect(screen.getByRole('button', { name: 'Soumettre à validation' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Valider' })).not.toBeInTheDocument()
  })

  it('un expert peut valider une donnée en attente', async () => {
    const onAction = vi.fn().mockResolvedValue(undefined)
    render(<WorkflowActions status="PENDING" canSubmit={false} isReviewer onAction={onAction} />)
    await userEvent.click(screen.getByRole('button', { name: 'Valider' }))
    expect(onAction).toHaveBeenCalledWith('validate', '')
  })

  it('le rejet exige un motif', async () => {
    const onAction = vi.fn().mockResolvedValue(undefined)
    render(<WorkflowActions status="PENDING" canSubmit={false} isReviewer onAction={onAction} />)
    await userEvent.click(screen.getByRole('button', { name: 'Rejeter' }))
    const dialog = screen.getByRole('dialog')
    const confirm = within(dialog).getByRole('button', { name: 'Rejeter' })
    expect(confirm).toBeDisabled()
    await userEvent.type(within(dialog).getByLabelText(/Motif du rejet/), 'Source illisible')
    expect(confirm).toBeEnabled()
    await userEvent.click(confirm)
    expect(onAction).toHaveBeenCalledWith('reject', 'Source illisible')
  })

  it('affiche l’erreur du serveur (ex. validation sans source)', async () => {
    const onAction = vi.fn().mockRejectedValue(new Error('Une source documentaire doit être associée avant validation.'))
    render(<WorkflowActions status="DRAFT" canSubmit isReviewer onAction={onAction} />)
    await userEvent.click(screen.getByRole('button', { name: 'Valider' }))
    expect(await screen.findByText(/source documentaire doit être associée/)).toBeInTheDocument()
  })

  it('rien à faire sur une donnée validée pour un non-expert', () => {
    const { container } = render(<WorkflowActions status="VALIDATED" canSubmit isReviewer={false} onAction={vi.fn()} />)
    expect(container).toBeEmptyDOMElement()
  })
})
