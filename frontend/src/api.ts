// Thin fetch wrappers for the Reviewer-Lens FastAPI backend.
// Requests go through Vite's dev proxy (see vite.config.ts) to /api -> :8000.

import { getStoredToken } from './auth/AuthContext'

export type JobStatusValue = 'processing' | 'done' | 'error' | 'approved'
export type PipelineStage = 'parsing' | 'literature' | 'architecture' | 'alignment' | 'aggregating' | null

export interface User {
  id: string
  name: string
  email: string
  role: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export interface ReviewResult {
  report_id: string
  composite_score: number
  literature_score: number
  architecture_score: number
  alignment_score: number
  citation_resolution_rate: number
  embedding_alignment_score: number
  all_flags: string[]
  literature_flags: string[]
  architecture_flags: string[]
  alignment_flags: string[]
  suggestions: string[]
  parse_warnings: string[]
  research_gap_summary: string
}

export interface JobStatusResponse {
  status: JobStatusValue
  stage: PipelineStage
  result: ReviewResult | null
  error: string | null
}

export interface HealthResponse {
  status: string
  groq_configured: boolean
}

export interface FlagItem {
  text: string
  source: string
  included: boolean
}

export interface SuggestionItem {
  text: string
  included: boolean
}

export interface ReviewSummary {
  id: string
  filename: string
  status: JobStatusValue
  stage: PipelineStage
  composite_score: number
  created_at: string
  approved_at: string | null
}

export interface ReviewDetail extends ReviewSummary {
  error: string | null
  literature_score: number
  architecture_score: number
  alignment_score: number
  citation_resolution_rate: number
  embedding_alignment_score: number
  literature_flags: string[]
  architecture_flags: string[]
  alignment_flags: string[]
  parse_warnings: string[]
  research_gap_summary: string
  all_flags: FlagItem[]
  suggestions: SuggestionItem[]
  report_ready: boolean
  final_report_ready: boolean
  approved_by_name: string | null
}

async function parseErrorDetail(res: Response, fallback: string): Promise<string> {
  try {
    const body = await res.json()
    if (typeof body?.detail === 'string') return body.detail
  } catch {
    // ignore — fall through to fallback message
  }
  return fallback
}

function authHeaders(token?: string | null): Record<string, string> {
  const t = token ?? getStoredToken()
  return t ? { Authorization: `Bearer ${t}` } : {}
}

async function authedFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const res = await fetch(input, { ...init, headers: { ...authHeaders(), ...(init.headers || {}) } })
  if (res.status === 401) {
    // Token missing/expired — surface a consistent, catchable error so
    // callers can bounce back to /login rather than rendering garbage.
    throw new Error('UNAUTHORIZED')
  }
  return res
}

// --- Auth -----------------------------------------------------------------

export async function register(name: string, email: string, password: string): Promise<AuthResponse> {
  const res = await fetch('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, password }),
  })
  if (!res.ok) throw new Error(await parseErrorDetail(res, 'Could not create an account.'))
  return res.json()
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const res = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) throw new Error(await parseErrorDetail(res, 'Could not sign in.'))
  return res.json()
}

export async function getMe(token: string): Promise<User> {
  const res = await fetch('/api/auth/me', { headers: authHeaders(token) })
  if (!res.ok) throw new Error('Session expired.')
  return res.json()
}

// --- Review pipeline --------------------------------------------------------

export async function startReview(file: File): Promise<{ job_id: string }> {
  const form = new FormData()
  form.append('file', file)

  const res = await authedFetch('/api/review', { method: 'POST', body: form })
  if (!res.ok) {
    throw new Error(await parseErrorDetail(res, 'Failed to start the review.'))
  }
  return res.json()
}

export async function getReviewStatus(jobId: string): Promise<JobStatusResponse> {
  const res = await authedFetch(`/api/review/${jobId}/status`)
  if (!res.ok) {
    throw new Error(await parseErrorDetail(res, 'Failed to fetch review status.'))
  }
  return res.json()
}

export async function getReviewDetail(jobId: string): Promise<ReviewDetail> {
  const res = await authedFetch(`/api/review/${jobId}`)
  if (!res.ok) {
    throw new Error(await parseErrorDetail(res, 'Failed to fetch review detail.'))
  }
  return res.json()
}

export async function listReviews(): Promise<ReviewSummary[]> {
  const res = await authedFetch('/api/reviews')
  if (!res.ok) {
    throw new Error(await parseErrorDetail(res, 'Failed to fetch review history.'))
  }
  return res.json()
}

export interface ApprovePayload {
  all_flags: FlagItem[]
  suggestions: SuggestionItem[]
  research_gap_summary: string
}

export async function approveReview(jobId: string, payload: ApprovePayload): Promise<ReviewDetail> {
  const res = await authedFetch(`/api/review/${jobId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    throw new Error(await parseErrorDetail(res, 'Failed to approve this review.'))
  }
  return res.json()
}

export async function getHealth(): Promise<HealthResponse> {
  const res = await fetch('/api/health')
  if (!res.ok) {
    throw new Error('Backend health check failed.')
  }
  return res.json()
}

/** Downloads the report through an authenticated fetch (a plain <a href>
 * can't carry the Authorization header) and saves it via an in-memory
 * object URL + a synthetic click. */
export async function downloadReport(reportId: string, suggestedName: string): Promise<void> {
  const res = await authedFetch(`/api/report/${reportId}`)
  if (!res.ok) {
    throw new Error(await parseErrorDetail(res, 'Failed to download the report.'))
  }
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = suggestedName
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
