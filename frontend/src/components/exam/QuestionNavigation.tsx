import { cn } from '../../lib/utils'
import { useUiFeedbackPress } from '../../hooks/useUiFeedbackPress'
import type { QuestionStatus } from '../../types/examSession'

interface QuestionNavigationProps {
  items: QuestionStatus[]
  onNavigate: (index: number) => void
  variant?: 'real' | 'practice' | 'review'
  className?: string
}

function QuestionNavigationButton({
  item,
  variant,
  onNavigate,
}: {
  item: QuestionStatus
  variant: 'real' | 'practice' | 'review'
  onNavigate: (index: number) => void
}) {
  const { feedbackClassName, triggerFeedback } = useUiFeedbackPress('nav')

  return (
    <button
      type="button"
      onClick={() => {
        triggerFeedback()
        onNavigate(item.questionIndex)
      }}
      className={cn(
        feedbackClassName,
        'relative flex h-12 w-12 items-center justify-center rounded-[1.1rem] font-black text-sm transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-900/40 focus-visible:ring-offset-2',
        item.tone === 'answered' &&
          'bg-[#dff4c7] text-[#457d17] hover:bg-[#d3efb4]',
        item.tone === 'unanswered' &&
          variant !== 'review' &&
          'bg-slate-100 text-slate-500 hover:bg-slate-200',
        item.tone === 'unanswered' &&
          variant === 'review' &&
          'bg-[#fff1c4] text-[#966b08] hover:bg-[#ffe8a8]',
        item.tone === 'correct' && 'bg-primary text-white hover:bg-primary/95',
        item.tone === 'incorrect' && 'bg-[#ff7c94] text-white hover:bg-[#f76f88]',
        item.isSelected && 'ring-2 ring-slate-900/50 ring-offset-2',
      )}
      aria-label={`Question ${item.questionIndex + 1}`}
      aria-current={item.isSelected ? 'step' : undefined}
    >
      {item.questionIndex + 1}
    </button>
  )
}

export function QuestionNavigation({
  items,
  onNavigate,
  variant = 'real',
  className,
}: QuestionNavigationProps) {
  return (
    <div className={cn('grid grid-cols-4 justify-items-center gap-3 p-1.5', className)}>
      {items.map((item) => (
        <QuestionNavigationButton
          key={item.questionId}
          item={item}
          onNavigate={onNavigate}
          variant={variant}
        />
      ))}
    </div>
  )
}
