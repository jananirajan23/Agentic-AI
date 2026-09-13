export default function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-700">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#EEF5F3" strokeWidth="2" className="h-4 w-4">
          <circle cx="10.5" cy="10.5" r="6" />
          <line x1="15.2" y1="15.2" x2="20" y2="20" strokeLinecap="round" />
        </svg>
      </span>
      <span className="font-serif text-[17px] font-semibold tracking-tight text-ink">Reviewer-Lens</span>
    </div>
  )
}
