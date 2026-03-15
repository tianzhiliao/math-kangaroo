export function QuestionCardSkeleton() {
  return (
    <div className="question-card question-card--has-graphics question-card--stem-single question-card--options-text animate-pulse">
      {/* Header Skeleton */}
      <section className="question-card__header">
        <div className="h-6 bg-slate-200 rounded w-3/4 mb-2"></div>
        <div className="h-6 bg-slate-200 rounded w-1/2"></div>
      </section>

      {/* Body Skeleton */}
      <section className="question-card__body">
        {/* Left Side Skeleton (Figure) */}
        <div className="question-card__figure bg-slate-100 border-slate-200">
          <div className="question-card__figure-inner flex items-center justify-center">
            <div className="w-24 h-24 bg-slate-200 rounded-full"></div>
          </div>
        </div>

        {/* Right Side Skeleton (Options) */}
        <div className="question-card__options">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="question-option question-option--text-only border-slate-100 bg-white">
              <div className="question-option__label bg-slate-200 text-transparent">A</div>
              <div className="question-option__content">
                <div className="h-4 bg-slate-200 rounded w-full mb-2"></div>
                <div className="h-4 bg-slate-200 rounded w-2/3"></div>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
