import { useState } from 'react'
import { downloadReport } from '../api'

interface DownloadButtonProps {
  reportId: string
  fileName: string
  label?: string
}

export default function DownloadButton({ reportId, fileName, label }: DownloadButtonProps) {
  const [isDownloading, setIsDownloading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleClick() {
    setError(null)
    setIsDownloading(true)
    try {
      await downloadReport(reportId, fileName)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Download failed.')
    } finally {
      setIsDownloading(false)
    }
  }

  return (
    <div className="flex flex-col items-end gap-1.5">
      <button
        onClick={handleClick}
        disabled={isDownloading}
        className="inline-flex items-center gap-2 rounded-lg bg-brand-700 px-4 py-2 text-[13px] font-semibold text-white shadow-card transition-colors hover:bg-brand-800 disabled:opacity-60"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-3.5 w-3.5">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v11m0 0l-4-4m4 4l4-4" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
        </svg>
        {isDownloading ? 'Preparing…' : label || 'Download Report (.docx)'}
      </button>
      {error && <p className="text-[11.5px] text-band-low">{error}</p>}
    </div>
  )
}
