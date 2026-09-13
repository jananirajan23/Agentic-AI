import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, XAxis, YAxis } from 'recharts'

type Band = 'good' | 'mid' | 'low'

const BAND_COLOR: Record<Band, string> = { good: '#2E6353', mid: '#9A6A16', low: '#A03A32' }
const BAND_BG: Record<Band, string> = { good: '#EAF3EF', mid: '#FBF1DF', low: '#FBEAE8' }
const BAND_LABEL: Record<Band, string> = { good: 'Strong', mid: 'Needs work', low: 'At risk' }

function bandFor(score: number): Band {
  if (score >= 75) return 'good'
  if (score >= 50) return 'mid'
  return 'low'
}

function ScoreRing({ score }: { score: number }) {
  const band = bandFor(score)
  const size = 176
  const strokeWidth = 13
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const clamped = Math.max(0, Math.min(100, score))
  const dashOffset = circumference * (1 - clamped / 100)

  return (
    <div className="relative flex shrink-0 items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="#EDEBE5" strokeWidth={strokeWidth} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={BAND_COLOR[band]}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 0.9s cubic-bezier(0.16, 1, 0.3, 1)' }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="font-serif text-[2.65rem] font-semibold leading-none tabular-nums text-ink">
          {score.toFixed(1)}
        </span>
        <span
          className="mt-2 rounded-full px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide"
          style={{ color: BAND_COLOR[band], backgroundColor: BAND_BG[band] }}
        >
          {BAND_LABEL[band]}
        </span>
      </div>
    </div>
  )
}

interface ScoreDashboardProps {
  composite: number
  literature: number
  architecture: number
  alignment: number
}

export default function ScoreDashboard({ composite, literature, architecture, alignment }: ScoreDashboardProps) {
  const data = [
    { name: 'Literature Survey', weight: '30%', score: literature, band: bandFor(literature) },
    { name: 'Architecture Structure', weight: '35%', score: architecture, band: bandFor(architecture) },
    { name: 'Alignment', weight: '35%', score: alignment, band: bandFor(alignment) },
  ]

  return (
    <div className="rounded-xl2 border border-line bg-paper-raised p-6 shadow-card sm:p-8">
      <div className="flex flex-col items-center gap-8 sm:flex-row sm:items-center sm:gap-10">
        <div className="flex flex-col items-center gap-2 text-center sm:items-start sm:text-left">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-ink-faint">Composite Score</p>
          <ScoreRing score={composite} />
        </div>

        <div className="w-full flex-1">
          <p className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-ink-faint">Score Breakdown</p>
          <ResponsiveContainer width="100%" height={148}>
            <BarChart data={data} layout="vertical" margin={{ top: 0, right: 28, bottom: 0, left: 0 }} barCategoryGap={18}>
              <XAxis type="number" domain={[0, 100]} hide />
              <YAxis
                type="category"
                dataKey="name"
                width={150}
                tickLine={false}
                axisLine={false}
                tick={{ fill: '#1B2028', fontSize: 12.5 }}
              />
              <Bar dataKey="score" radius={6} background={{ fill: '#EDEBE5', radius: 6 }} isAnimationActive maxBarSize={16}>
                {data.map((entry) => (
                  <Cell key={entry.name} fill={BAND_COLOR[entry.band]} />
                ))}
                <LabelList
                  dataKey="score"
                  position="right"
                  formatter={(value: unknown) => Number(value).toFixed(0)}
                  style={{ fill: '#1B2028', fontSize: 12.5, fontWeight: 600 }}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div className="mt-1 flex flex-wrap gap-x-5 gap-y-1 pl-0">
            {data.map((d) => (
              <span key={d.name} className="text-[11.5px] text-ink-faint">
                {d.name} weighted {d.weight}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
