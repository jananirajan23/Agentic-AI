import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getHealth, listReviews, type ReviewSummary } from '../api'
import TopBar from '../components/TopBar'

const STATUS_LABEL: Record<ReviewSummary['status'], string> = {
  processing: 'Processing',
  done: 'Awaiting faculty review',
  approved: 'Approved',
  error: 'Failed',
}

const STATUS_STYLE: Record<ReviewSummary['status'], string> = {
  processing: 'bg-band-midBg text-band-mid',
  done: 'bg-brand-100 text-brand-800',
  approved: 'bg-band-goodBg text-band-good',
  error: 'bg-band-lowBg text-band-low',
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
  } catch {
    return iso
  }
}

export default function DashboardPage() {
  const health = useQuery({ queryKey: ['health'], queryFn: getHealth })
  const reviews = useQuery({
    queryKey: ['reviews'],
    queryFn: listReviews,
    refetchInterval: (query) => (query.state.data?.some((r) => r.status === 'processing') ? 2000 : false),
  })

  const showSetupBanner = health.data && !health.data.groq_configured

  return (
    <div className="min-h-screen bg-paper">
      <TopBar
        right={
          <Link
            to="/review/new"
            className="rounded-lg bg-brand-700 px-3.5 py-2 text-[13px] font-semibold text-white shadow-card transition-colors hover:bg-brand-800"
          >
            + New Review
          </Link>
        }
      />

      {showSetupBanner && (
        <div className="border-b border-band-midBg bg-band-midBg/70 px-6 py-2.5 text-center text-[13px] text-band-mid">
          <strong className="font-semibold">Setup notice:</strong> <code className="font-mono">GROQ_API_KEY</code> is
          not configured on the backend — literature, architecture, and alignment scores will come back reduced
          until it's set.
        </div>
      )}

      <main className="mx-auto max-w-5xl px-6 py-12">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="font-serif text-2xl font-semibold text-ink">Review Dashboard</h1>
            <p className="mt-1 text-[13.5px] text-ink-muted">
              Every capstone report you've submitted for pre-review, and its current status.
            </p>
          </div>
        </div>

        {reviews.isLoading && <p className="text-[13.5px] text-ink-faint">Loading your reviews…</p>}

        {reviews.isError && (
          <p className="rounded-lg bg-band-lowBg px-4 py-3 text-[13.5px] text-band-low">
            Could not load your review history.
          </p>
        )}

        {reviews.data && reviews.data.length === 0 && (
          <div className="rounded-xl2 border border-dashed border-line bg-paper-raised p-10 text-center">
            <p className="text-[14.5px] text-ink-muted">No reviews yet.</p>
            <Link
              to="/review/new"
              className="mt-4 inline-block rounded-lg bg-brand-700 px-4 py-2 text-[13px] font-semibold text-white shadow-card transition-colors hover:bg-brand-800"
            >
              Upload your first report
            </Link>
          </div>
        )}

        {reviews.data && reviews.data.length > 0 && (
          <div className="overflow-hidden rounded-xl2 border border-line bg-paper-raised shadow-card">
            <table className="w-full text-left text-[13.5px]">
              <thead>
                <tr className="border-b border-line bg-line-soft/40 text-[11.5px] uppercase tracking-wide text-ink-faint">
                  <th className="px-5 py-3 font-semibold">Report</th>
                  <th className="px-5 py-3 font-semibold">Submitted</th>
                  <th className="px-5 py-3 font-semibold">Status</th>
                  <th className="px-5 py-3 font-semibold">Composite Score</th>
                </tr>
              </thead>
              <tbody>
                {reviews.data.map((r) => (
                  <tr key={r.id} className="border-b border-line last:border-0 hover:bg-line-soft/30">
                    <td className="px-5 py-3.5">
                      <Link to={`/review/${r.id}`} className="font-medium text-ink hover:text-brand-700">
                        {r.filename}
                      </Link>
                    </td>
                    <td className="px-5 py-3.5 text-ink-muted">{formatDate(r.created_at)}</td>
                    <td className="px-5 py-3.5">
                      <span className={`rounded-full px-2.5 py-0.5 text-[11.5px] font-semibold ${STATUS_STYLE[r.status]}`}>
                        {STATUS_LABEL[r.status]}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 tabular-nums text-ink">
                      {r.status === 'processing' || r.status === 'error' ? '—' : r.composite_score.toFixed(1)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  )
}
