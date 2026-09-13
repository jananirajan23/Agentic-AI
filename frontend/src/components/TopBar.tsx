import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import Logo from './Logo'

export default function TopBar({ right }: { right?: ReactNode }) {
  const { user, logout } = useAuth()

  return (
    <header className="sticky top-0 z-10 border-b border-line bg-paper/90 backdrop-blur-sm">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <Link to="/">
          <Logo />
        </Link>
        <div className="flex items-center gap-4">
          {right}
          {user && (
            <div className="flex items-center gap-3 border-l border-line pl-4">
              <span className="text-[13px] text-ink-muted">{user.name}</span>
              <button
                onClick={logout}
                className="text-[12.5px] font-medium text-ink-faint transition-colors hover:text-band-low"
              >
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
