import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  getReviewDetail,
  getReviewStatus,
  startReview,
  type ReviewDetail,
  type ReviewResult,
} from '../api'
import DownloadButton from '../components/DownloadButton'
import FlagsList from '../components/FlagsList'
import ProcessingView from '../components/ProcessingView'
import ReviewApprovalPanel from '../components/ReviewApprovalPanel'
import ScoreDashboard from '../components/ScoreDashboard'
import SuggestionsList from '../components/SuggestionsList'
import TopBar from '../components/TopBar'
import UploadPanel from '../components/UploadPanel'

function MeasuredMetrics({ result }: { result: Pick<ReviewResult, 'citation_resolution_rate' | 'embedding_alignment_score'> }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <div className="rounded-xl2 border border-line bg-paper-raised p-5 shadow-card">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-ink-faint">
          Citation Resolution Rate
        </p>
        <p className="mt-1.5 font-serif text-2xl font-semibold text-ink">
          {(result.citation_resolution_rate * 100).toFixed(0)}%
        </p>
        <p className="mt-1 text-[12px] leading-relaxed text-ink-faint">
          Citations found in the report that were resolved against Semantic Scholar.
        </p>
      </div>
      <div className="rounded-xl2 border border-line bg-paper-raised p-5 shadow-card">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-ink-faint">
          Embedding Alignment Score
        </p>
        <p className="mt-1.5 font-serif text-2xl font-semibold text-ink">
          {result.embedding_alignment_score.toFixed(1)}
        </p>
        <p className="mt-1 text-[12px] leading-relaxed text-ink-faint">
          Deterministic cosine-similarity match between diagram components and module text.
        </p>
      </div>
    </div>
  )
}

/** New-upload flow: shows the drop zone, kicks off /api/review, then
 * redirects to /review/:jobId so the rest of the workflow (processing,
 * faculty approval, final download) lives at a stable, resumable URL. */
function NewReviewFlow() {
  const navigate = useNavigate()
  const [errorMessage, setErrorMessage] = useState('')

  const startReviewMutation = useMutation({
    mutationFn: startReview,
    onSuccess: (data) => navigate(`/review/${data.job_id}`, { replace: true }),
    onError: (err: Error) => setErrorMessage(err.message || 'Could not start the review. Please try again.'),
  })

  return (
    <div className="mx-auto max-w-5xl px-6 py-14 sm:py-20">
      <UploadPanel onSubmit={(file) => startReviewMutation.mutate(file)} />
      {errorMessage && (
        <p className="mx-auto mt-4 max-w-2xl text-center text-[13px] text-band-low">{errorMessage}</p>
      )}
    </div>
  )
}

/** Existing-job flow: polls status while processing, then renders the
 * faculty-approval panel (status "done") or the final read-only result
 * with a download button (status "approved"). */
function ExistingReviewFlow({ jobId }: { jobId: string }) {
  const queryClient = useQueryClient()

  const statusQuery = useQuery({
    queryKey: ['review-status', jobId],
    queryFn: () => getReviewStatus(jobId),
    refetchInterval: (query) => (query.state.data?.status === 'processing' ? 1500 : false),
  })

  const status = statusQuery.data?.status
  const detailQuery = useQuery({
    // Including `status` in the key forces a fresh fetch the moment the
    // job transitions processing -> done -> approved, instead of caching
    // (and silently keeping forever) the near-empty snapshot fetched
    // while the pipeline was still running — that mismatch was exactly
    // what made the results screen briefly render every score as 0.
    queryKey: ['review-detail', jobId, status],
    queryFn: () => getReviewDetail(jobId),
    enabled: !!status,
  })

  useEffect(() => {
    queryClient.invalidateQueries({ queryKey: ['reviews'] })
  }, [statusQuery.data?.status, queryClient])

  function handleApproved(updated: ReviewDetail) {
    queryClient.setQueryData(['review-detail', jobId, 'approved'], updated)
    queryClient.setQueryData(['review-status', jobId], (prev: typeof statusQuery.data) =>
      prev ? { ...prev, status: 'approved' as const } : prev,
    )
    queryClient.invalidateQueries({ queryKey: ['reviews'] })
  }

  if (statusQuery.isLoading) {
    return <p className="mx-auto max-w-xl px-6 py-20 text-center text-[13.5px] text-ink-faint">Loading…</p>
  }

  if (statusQuery.isError || !statusQuery.data) {
    return (
      <p className="mx-auto max-w-xl px-6 py-20 text-center text-[13.5px] text-band-low">
        Could not load this review.
      </p>
    )
  }

  if (statusQuery.data.status === 'error') {
    return (
      <div className="mx-auto w-full max-w-lg px-6 py-20 text-center">
        <h2 className="font-serif text-2xl font-semibold text-ink">Something went wrong</h2>
        <p className="mx-auto mt-2 max-w-sm text-[14px] leading-relaxed text-ink-muted">
          {statusQuery.data.error || 'The review pipeline hit an unexpected error.'}
        </p>
      </div>
    )
  }

  if (statusQuery.data.status === 'processing') {
    return (
      <div className="mx-auto max-w-5xl px-6 py-14 sm:py-20">
        <ProcessingView stage={statusQuery.data.stage} fileName={detailQuery.data?.filename || ''} />
      </div>
    )
  }

  if (!detailQuery.data) {
    return <p className="mx-auto max-w-xl px-6 py-20 text-center text-[13.5px] text-ink-faint">Loading results…</p>
  }

  const detail = detailQuery.data

  return (
    <div className="mx-auto max-w-3xl animate-fadeUp space-y-6 px-6 py-14 sm:py-20">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-serif text-2xl font-semibold text-ink">
            {detail.status === 'approved' ? 'Approved Review' : 'Review Results — Faculty Approval Needed'}
          </h2>
          <p className="text-[13.5px] text-ink-muted">{detail.filename}</p>
        </div>
        {detail.status === 'approved' && (
          <DownloadButton
            reportId={detail.id}
            fileName={`reviewer_lens_final_${detail.id.slice(0, 8)}.docx`}
            label="Download Final Report (.docx)"
          />
        )}
      </div>

      <ScoreDashboard
        composite={detail.composite_score}
        literature={detail.literature_score}
        architecture={detail.architecture_score}
        alignment={detail.alignment_score}
      />

      <MeasuredMetrics
        result={{
          citation_resolution_rate: detail.citation_resolution_rate,
          embedding_alignment_score: detail.embedding_alignment_score,
        }}
      />

      {detail.status === 'done' && <ReviewApprovalPanel detail={detail} onApproved={handleApproved} />}

      {detail.status === 'approved' && (
        <>
          {detail.research_gap_summary && (
            <div className="rounded-xl2 border border-line bg-paper-raised p-6 shadow-card sm:p-8">
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-ink-faint">
                Research Gap Summary
              </p>
              <p className="text-[13.5px] leading-relaxed text-ink">{detail.research_gap_summary}</p>
            </div>
          )}

          <FlagsList
            parseWarnings={detail.parse_warnings}
            literatureFlags={detail.all_flags.filter((f) => f.source === 'literature' && f.included).map((f) => f.text)}
            architectureFlags={detail.all_flags.filter((f) => f.source === 'architecture' && f.included).map((f) => f.text)}
            alignmentFlags={detail.all_flags.filter((f) => f.source === 'alignment' && f.included).map((f) => f.text)}
          />

          <SuggestionsList suggestions={detail.suggestions.filter((s) => s.included).map((s) => s.text)} />

          <div className="flex items-start gap-2.5 rounded-xl border border-line-soft bg-line-soft/40 px-4 py-3.5 text-[12.5px] leading-relaxed text-ink-muted">
            <span>
              Approved by {detail.approved_by_name || 'a faculty reviewer'}. This report reflects only the items the
              reviewer chose to include.
            </span>
          </div>
        </>
      )}
    </div>
  )
}

export default function ReviewWorkspacePage() {
  const { jobId } = useParams<{ jobId: string }>()

  return (
    <div className="min-h-screen bg-paper">
      <TopBar />
      {jobId ? <ExistingReviewFlow jobId={jobId} /> : <NewReviewFlow />}
    </div>
  )
}
