import { useCallback, useRef, useState, type DragEvent } from 'react'

interface UploadPanelProps {
  onSubmit: (file: File) => void
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

function isPdf(file: File): boolean {
  return file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
}

export default function UploadPanel({ onSubmit }: UploadPanelProps) {
  const [file, setFile] = useState<File | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const acceptFile = useCallback((candidate: File | undefined | null) => {
    if (!candidate) return
    if (!isPdf(candidate)) {
      setError('Only PDF files are supported. Please choose a .pdf report.')
      setFile(null)
      return
    }
    setError(null)
    setFile(candidate)
  }, [])

  const handleDrop = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault()
      setIsDragging(false)
      acceptFile(e.dataTransfer.files?.[0])
    },
    [acceptFile],
  )

  return (
    <div className="mx-auto w-full max-w-2xl animate-fadeUp">
      <div className="mb-8 text-center">
        <h1 className="font-serif text-4xl font-semibold tracking-tight text-ink">
          Pre-review your capstone report
        </h1>
        <p className="mx-auto mt-3 max-w-lg text-[15px] leading-relaxed text-ink-muted">
          Upload a PDF and three verification agents will check your literature survey,
          architecture diagram, and module alignment — before it reaches faculty review.
        </p>
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault()
          setIsDragging(true)
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={[
          'group relative flex cursor-pointer flex-col items-center justify-center rounded-xl2 border-2 border-dashed px-8 py-14 text-center transition-all duration-200',
          isDragging
            ? 'border-brand-400 bg-brand-50'
            : 'border-line bg-paper-raised hover:border-brand-300 hover:bg-brand-50/40',
        ].join(' ')}
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          className="hidden"
          onChange={(e) => acceptFile(e.target.files?.[0])}
        />

        <div
          className={[
            'mb-4 flex h-14 w-14 items-center justify-center rounded-full transition-colors',
            isDragging ? 'bg-brand-200' : 'bg-brand-100 group-hover:bg-brand-200',
          ].join(' ')}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            className="h-6 w-6 text-brand-700"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 16V4m0 0L7 9m5-5l5 5" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v2.5A1.5 1.5 0 0 0 5.5 20h13a1.5 1.5 0 0 0 1.5-1.5V16" />
          </svg>
        </div>

        <p className="text-[15px] font-medium text-ink">
          Drag and drop your report here, or <span className="text-brand-700 underline underline-offset-2">browse</span>
        </p>
        <p className="mt-1.5 text-[13px] text-ink-faint">PDF only, up to ~50 pages</p>
      </div>

      {error && (
        <p className="mt-3 flex items-center gap-1.5 text-[13px] text-band-low">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-3.5 w-3.5 shrink-0">
            <circle cx="12" cy="12" r="9" />
            <path strokeLinecap="round" d="M12 8v5M12 16h.01" />
          </svg>
          {error}
        </p>
      )}

      {file && (
        <div className="mt-4 flex items-center justify-between rounded-xl border border-line bg-paper-raised px-4 py-3 shadow-card animate-fadeUp">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-100 text-brand-700">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-4.5 w-4.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M7 3h7l5 5v11a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M14 3v5h5" />
              </svg>
            </div>
            <div className="min-w-0">
              <p className="truncate text-[13.5px] font-medium text-ink">{file.name}</p>
              <p className="text-[12px] text-ink-faint">{formatBytes(file.size)}</p>
            </div>
          </div>
          <button
            onClick={(e) => {
              e.stopPropagation()
              setFile(null)
              if (inputRef.current) inputRef.current.value = ''
            }}
            className="ml-3 shrink-0 rounded-md p-1.5 text-ink-faint transition-colors hover:bg-line-soft hover:text-ink"
            aria-label="Remove file"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4">
              <path strokeLinecap="round" d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </div>
      )}

      <button
        disabled={!file}
        onClick={() => file && onSubmit(file)}
        className={[
          'mt-6 w-full rounded-xl py-3.5 text-[14.5px] font-semibold tracking-wide transition-all duration-200',
          file
            ? 'bg-brand-700 text-white shadow-card hover:bg-brand-800 active:scale-[0.99]'
            : 'cursor-not-allowed bg-line-soft text-ink-faint',
        ].join(' ')}
      >
        Run Review
      </button>
    </div>
  )
}
