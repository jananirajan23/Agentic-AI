import type { PipelineStage } from '../api'

interface Step {
  key: NonNullable<PipelineStage>
  title: string
  description: string
}

const STEPS: Step[] = [
  {
    key: 'parsing',
    title: 'Parsing document',
    description: 'Extracting the problem statement, literature survey, module text, and diagrams from the PDF.',
  },
  {
    key: 'literature',
    title: 'Literature survey agent',
    description: 'Resolving citations against Semantic Scholar and scoring relevance & recency.',
  },
  {
    key: 'architecture',
    title: 'Architecture structure agent',
    description: 'Reading the architecture diagram with a vision model to identify components and data flow.',
  },
  {
    key: 'alignment',
    title: 'Alignment agent',
    description: 'Comparing diagram components against the documented module description.',
  },
  {
    key: 'aggregating',
    title: 'Generating report',
    description: 'Computing the composite score, drafting suggestions, and building the downloadable report.',
  },
]

function CheckIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" className="h-4 w-4">
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  )
}

interface ProcessingViewProps {
  stage: PipelineStage
  fileName: string
}

export default function ProcessingView({ stage, fileName }: ProcessingViewProps) {
  const currentIndex = stage ? STEPS.findIndex((s) => s.key === stage) : 0

  return (
    <div className="mx-auto w-full max-w-xl animate-fadeUp">
      <div className="mb-9 text-center">
        <h2 className="font-serif text-2xl font-semibold text-ink">Reviewing your report</h2>
        <p className="mt-2 text-[14px] text-ink-muted">
          Running the agent pipeline on <span className="font-medium text-ink">{fileName}</span>
        </p>
      </div>

      <div className="rounded-xl2 border border-line bg-paper-raised p-6 shadow-card sm:p-8">
        <ol className="relative">
          {STEPS.map((step, i) => {
            const isComplete = i < currentIndex
            const isActive = i === currentIndex
            const isLast = i === STEPS.length - 1

            return (
              <li key={step.key} className="relative flex gap-4 pb-8 last:pb-0">
                {!isLast && (
                  <span
                    className={[
                      'absolute left-[15px] top-8 h-[calc(100%-1.25rem)] w-px transition-colors duration-300',
                      isComplete ? 'bg-brand-400' : 'bg-line',
                    ].join(' ')}
                  />
                )}
                <span
                  className={[
                    'relative flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 text-[12px] font-semibold transition-all duration-300',
                    isComplete
                      ? 'border-brand-500 bg-brand-500 text-white'
                      : isActive
                        ? 'border-brand-500 bg-brand-50 text-brand-700 animate-pulseSoft'
                        : 'border-line bg-paper-raised text-ink-faint',
                  ].join(' ')}
                >
                  {isComplete ? <CheckIcon /> : i + 1}
                </span>
                <div className="pt-0.5">
                  <p
                    className={[
                      'text-[14.5px] font-medium transition-colors duration-300',
                      isComplete || isActive ? 'text-ink' : 'text-ink-faint',
                    ].join(' ')}
                  >
                    {step.title}
                  </p>
                  <p
                    className={[
                      'mt-0.5 text-[13px] leading-relaxed transition-colors duration-300',
                      isActive ? 'text-ink-muted' : 'text-ink-faint',
                    ].join(' ')}
                  >
                    {step.description}
                  </p>
                </div>
              </li>
            )
          })}
        </ol>
      </div>
    </div>
  )
}
