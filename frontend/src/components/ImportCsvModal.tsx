import { FileUp } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { Button } from '@/components/ui/Button'
import { Alert } from '@/components/ui/Feedback'
import { Modal } from '@/components/ui/Modal'
import { ApiError } from '@/services/api'
import type { ImportBatch } from '@/types/animal'

/** Import CSV générique : envoi du fichier puis compte rendu ligne par ligne. */
export function ImportCsvModal({
  open,
  title,
  help,
  onClose,
  onImport,
}: {
  open: boolean
  title: string
  help: ReactNode
  onClose: () => void
  onImport: (file: File) => Promise<ImportBatch>
}) {
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [report, setReport] = useState<ImportBatch | null>(null)

  const close = () => {
    setFile(null)
    setError(null)
    setReport(null)
    onClose()
  }

  const submit = async () => {
    if (!file) {
      setError('Choisissez un fichier CSV.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      setReport(await onImport(file))
    } catch (e) {
      setError(e instanceof ApiError ? Object.values(e.fieldErrors).flat().join(' ') || e.message : e instanceof Error ? e.message : 'Import impossible.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open={open}
      title={title}
      onClose={close}
      footer={
        report ? (
          <Button onClick={close}>Fermer</Button>
        ) : (
          <>
            <Button variant="secondary" onClick={close}>
              Annuler
            </Button>
            <Button onClick={submit} loading={busy} icon={<FileUp className="size-4" />}>
              Importer
            </Button>
          </>
        )
      }
    >
      {report ? (
        <div className="space-y-3">
          <Alert tone={report.error_rows ? 'warning' : 'success'} title={report.status_label}>
            {report.created_rows} ligne(s) importée(s), {report.error_rows} en erreur sur {report.total_rows}.
          </Alert>
          {report.errors.length > 0 && (
            <ul className="max-h-60 space-y-1 overflow-y-auto rounded-lg border border-slate-200 p-3 text-sm">
              {report.errors.map((e, i) => (
                <li key={i}>
                  <span className="font-medium text-slate-700">Ligne {e.line ?? '—'} :</span>{' '}
                  <span className="text-red-700">{e.error}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : (
        <div className="space-y-4 text-sm text-slate-600">
          {error && <Alert tone="error">{error}</Alert>}
          <div>{help}</div>
          <input
            type="file"
            accept=".csv,text/csv"
            aria-label="Fichier CSV"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="block w-full text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-brand-50 file:px-3 file:py-2 file:font-medium file:text-brand-700"
          />
        </div>
      )}
    </Modal>
  )
}
