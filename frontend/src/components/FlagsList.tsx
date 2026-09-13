import type { ReactNode } from 'react'

interface FlagGroup {
  label: string
  flags: string[]
  icon: ReactNode
}

interface FlagsListProps {
  parseWarnings: string[]
  literatureFlags: string[]
  architectureFlags: string[]
  alignmentFlags: string[]
}

const iconProps = {
  xmlns: 'http://www.w3.org/2000/svg',
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.7,
  className: 'h-4 w-4',
} as const

function ParserIcon() {
  return (
    <svg {...iconProps}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M7 3h7l5 5v11a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M14 3v5h5" />
    </svg>
  )
}
function BookIcon() {
  return (
    <svg {...iconProps}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V4H6.5A2.5 2.5 0 0 0 4 6.5v13Z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
    </svg>
  )
}
function LayersIcon() {
  return (
    <svg {...iconProps}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 3l9 5-9 5-9-5 9-5Z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 13l9 5 9-5" />
    </svg>
  )
}
function LinkIcon() {
  return (
    <svg {...iconProps}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6M8 17H6a4 4 0 0 1 0-8h2M16 7h2a4 4 0 0 1 0 8h-2" />
    </svg>
  )
}

export default function FlagsList({ parseWarnings, literatureFlags, architectureFlags, alignmentFlags }: FlagsListProps) {
  const groups: FlagGroup[] = [
    { label: 'Document Parsing', flags: parseWarnings, icon: <ParserIcon /> },
    { label: 'Literature Survey', flags: literatureFlags, icon: <BookIcon /> },
    { label: 'Architecture Structure', flags: architectureFlags, icon: <LayersIcon /> },
    { label: 'Alignment', flags: alignmentFlags, icon: <LinkIcon /> },
  ].filter((g) => g.flags.length > 0)

  return (
    <div className="rounded-xl2 border border-line bg-paper-raised p-6 shadow-card sm:p-8">
      <div className="mb-5 flex items-center gap-2">
        <span className="flex h-6 w-6 items-center justify-center rounded-md bg-band-lowBg text-band-low">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-3.5 w-3.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v16M4 4h11l-1.5 3L15 10H4" />
          </svg>
        </span>
        <h3 className="text-[15px] font-semibold text-ink">Flagged Issues</h3>
      </div>

      {groups.length === 0 ? (
        <p className="rounded-lg bg-band-goodBg px-4 py-3 text-[13.5px] text-band-good">
          No issues were flagged across any of the three checks.
        </p>
      ) : (
        <div className="space-y-6">
          {groups.map((group) => (
            <div key={group.label}>
              <div className="mb-2.5 flex items-center gap-2 text-ink-muted">
                {group.icon}
                <p className="text-[12.5px] font-semibold uppercase tracking-wide">{group.label}</p>
                <span className="text-[11px] text-ink-faint">({group.flags.length})</span>
              </div>
              <ul className="space-y-2">
                {group.flags.map((flag, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2.5 rounded-lg border border-band-lowBg bg-band-lowBg/60 px-3.5 py-2.5 text-[13.5px] leading-relaxed text-ink"
                  >
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-band-low" />
                    {flag}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
