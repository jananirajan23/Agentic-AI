interface SuggestionsListProps {
  suggestions: string[]
}

export default function SuggestionsList({ suggestions }: SuggestionsListProps) {
  return (
    <div className="rounded-xl2 border border-brand-200 bg-brand-50/50 p-6 shadow-card sm:p-8">
      <div className="mb-5 flex items-center gap-2">
        <span className="flex h-6 w-6 items-center justify-center rounded-md bg-brand-200 text-brand-800">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-3.5 w-3.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 18h6M10 21h4M12 3a6 6 0 0 0-3.6 10.8c.5.4.85 1 .95 1.7h5.3c.1-.7.45-1.3.95-1.7A6 6 0 0 0 12 3Z" />
          </svg>
        </span>
        <h3 className="text-[15px] font-semibold text-ink">Improvement Suggestions</h3>
      </div>

      {suggestions.length === 0 ? (
        <p className="text-[13.5px] text-ink-muted">No suggestions to show.</p>
      ) : (
        <ol className="space-y-3">
          {suggestions.map((suggestion, i) => (
            <li
              key={i}
              className="flex items-start gap-3 rounded-lg border border-brand-200 bg-paper-raised px-4 py-3 text-[13.5px] leading-relaxed text-ink"
            >
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-700 text-[11px] font-semibold text-white">
                {i + 1}
              </span>
              {suggestion}
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
