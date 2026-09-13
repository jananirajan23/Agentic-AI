import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import Logo from '../components/Logo'

export default function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (password.length < 6) {
      setError('Password must be at least 6 characters.')
      return
    }
    setIsSubmitting(true)
    try {
      await register(name, email, password)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create an account.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-paper px-6">
      <div className="w-full max-w-sm animate-fadeUp">
        <div className="mb-8 flex justify-center">
          <Logo />
        </div>

        <div className="rounded-xl2 border border-line bg-paper-raised p-7 shadow-card">
          <h1 className="font-serif text-xl font-semibold text-ink">Create a faculty account</h1>
          <p className="mt-1 text-[13px] text-ink-muted">
            Used to review, approve, and download capstone pre-review reports.
          </p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div>
              <label className="mb-1.5 block text-[12.5px] font-medium text-ink-muted" htmlFor="name">
                Full name
              </label>
              <input
                id="name"
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded-lg border border-line bg-paper px-3.5 py-2.5 text-[13.5px] text-ink outline-none transition-colors focus:border-brand-400"
                placeholder="Dr. Jane Reviewer"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-[12.5px] font-medium text-ink-muted" htmlFor="email">
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-line bg-paper px-3.5 py-2.5 text-[13.5px] text-ink outline-none transition-colors focus:border-brand-400"
                placeholder="you@institution.edu"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-[12.5px] font-medium text-ink-muted" htmlFor="password">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-line bg-paper px-3.5 py-2.5 text-[13.5px] text-ink outline-none transition-colors focus:border-brand-400"
                placeholder="At least 6 characters"
              />
            </div>

            {error && (
              <p className="rounded-lg bg-band-lowBg px-3 py-2 text-[12.5px] text-band-low">{error}</p>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full rounded-xl bg-brand-700 py-2.5 text-[13.5px] font-semibold text-white shadow-card transition-colors hover:bg-brand-800 disabled:opacity-60"
            >
              {isSubmitting ? 'Creating account…' : 'Create account'}
            </button>
          </form>
        </div>

        <p className="mt-5 text-center text-[13px] text-ink-muted">
          Already have an account?{' '}
          <Link to="/login" className="font-medium text-brand-700 underline-offset-2 hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
