import { LoaderCircle, Square, Volume2 } from 'lucide-react'
import { useStemAudioAvailability } from '../../hooks/useStemAudioAvailability'
import { useStemAudioPlayer } from '../../hooks/useStemAudioPlayer'
import { cn } from '../../lib/utils'
import type { QuestionAudioTarget } from '../../lib/questionIdentity'
import type { Question } from '../../types/exam'
import { SvgGraphic } from './SvgGraphic'

interface QuestionCardProps {
  audioTarget: QuestionAudioTarget
  question: Question
  selectedOption?: string | null
  onSelectOption?: (optionKey: string) => void
  mode?: 'interactive' | 'review'
  correctOption?: string
  className?: string
}

export function QuestionCard({
  audioTarget,
  question,
  selectedOption,
  onSelectOption,
  mode = 'interactive',
  correctOption,
  className,
}: QuestionCardProps) {
  const optionEntries = Object.entries(question.options)
  const options = Object.values(question.options)
  const stemGraphics = question.stem_graphics ?? []
  const stemGraphicCount = stemGraphics.length
  const hasStemGraphics = stemGraphicCount > 0
  const hasTextOnlyOptions =
    options.length > 0 &&
    options.every((option) => (option.graphics?.length ?? 0) === 0)
  const hasGraphicOnlyOptions =
    options.length > 0 &&
    options.every(
      (option) => (option.graphics?.length ?? 0) > 0 && !(option.text ?? '').trim(),
    )
  const hasFiveOptions = optionEntries.length === 5
  const hasMixedOptions = !hasTextOnlyOptions && !hasGraphicOnlyOptions
  const isInteractive = mode === 'interactive'
  const {
    canPlay,
    error: stemAudioError,
    status: stemAudioStatus,
    togglePlayback,
  } = useStemAudioPlayer({
    audioTarget,
    stemText: question.stem_text,
  })
  const {
    status: stemAudioAvailabilityStatus,
    message: stemAudioAvailabilityMessage,
  } = useStemAudioAvailability()
  const isStemAudioPlaying = stemAudioStatus === 'playing'
  const isStemAudioLoading = stemAudioStatus === 'loading'
  const showStemAudioButton =
    canPlay && stemAudioAvailabilityStatus === 'available'
  const stemAudioFeedback =
    stemAudioError ??
    (canPlay && stemAudioAvailabilityStatus === 'unavailable'
      ? stemAudioAvailabilityMessage
      : null)
  const stemAudioLabel = isStemAudioPlaying
    ? 'Stop reading question'
    : isStemAudioLoading
      ? 'Stop loading question audio'
      : 'Read question aloud'

  return (
    <div
      className={cn(
        'question-card',
        className,
        hasStemGraphics ? 'question-card--has-graphics' : 'question-card--no-graphics',
        stemGraphicCount === 1 ? 'question-card--stem-single' : 'question-card--stem-multi',
        hasTextOnlyOptions && 'question-card--options-text',
        hasGraphicOnlyOptions && 'question-card--options-graphics',
        hasGraphicOnlyOptions && hasFiveOptions && 'question-card--options-graphics-five',
        hasGraphicOnlyOptions && hasStemGraphics && 'question-card--options-graphics-with-stem',
        hasGraphicOnlyOptions && !hasStemGraphics && 'question-card--options-graphics-no-stem',
        hasMixedOptions && 'question-card--options-mixed',
      )}
    >
      <section className="question-card__header">
        <div className="question-card__stem-shell">
          <h2 className="question-card__stem">{question.stem_text}</h2>
          {showStemAudioButton && (
            <button
              type="button"
              aria-label={stemAudioLabel}
              aria-busy={isStemAudioLoading}
              aria-pressed={isStemAudioPlaying}
              className={cn(
                'question-card__stem-audio',
                isStemAudioPlaying && 'question-card__stem-audio--playing',
                stemAudioStatus === 'error' && 'question-card__stem-audio--error',
              )}
              onClick={togglePlayback}
              title={stemAudioLabel}
            >
              {isStemAudioLoading ? (
                <LoaderCircle className="h-5 w-5 animate-spin" />
              ) : isStemAudioPlaying ? (
                <Square className="h-4 w-4 fill-current" />
              ) : (
                <Volume2 className="h-5 w-5" />
              )}
            </button>
          )}
        </div>
        {stemAudioFeedback && (
          <p className="question-card__stem-audio-error">{stemAudioFeedback}</p>
        )}
      </section>

      <section
        className={cn(
          'question-card__body',
          !hasStemGraphics && 'question-card__body--no-figure',
        )}
      >
        {hasStemGraphics && (
          <div className="question-card__figure">
            <div
              className={cn(
                'question-card__figure-inner',
                stemGraphicCount > 1 && 'question-card__figure-inner--grid',
              )}
            >
              {stemGraphics.map((graphic) => (
                <SvgGraphic
                  key={graphic.id}
                  graphic={graphic}
                  className="question-card__figure-svg"
                  loadingFallback={
                    <div className="question-card__figure-empty">
                      <span>Loading image...</span>
                    </div>
                  }
                  fallback={
                    <div className="question-card__figure-empty">
                      <span>Image unavailable</span>
                    </div>
                  }
                />
              ))}
            </div>
          </div>
        )}

        <div className="question-card__options">
          {optionEntries.map(([key, option]) => {
            const isSelected = selectedOption === key
            const isCorrectOption = correctOption === key
            const isWrongSelection = mode === 'review' && isSelected && !isCorrectOption
            const optionText = (option.text ?? '').trim()
            const optionGraphicCount = option.graphics?.length ?? 0
            const hasOptionGraphics = optionGraphicCount > 0
            const hasOptionText = optionText.length > 0
            const isGraphicOnlyOption = hasOptionGraphics && !hasOptionText
            const isTextOnlyOption = !hasOptionGraphics
            const isMixedOption = hasOptionGraphics && hasOptionText

            let reviewBadge: string | null = null
            if (mode === 'review') {
              if (isCorrectOption && isSelected) {
                reviewBadge = 'Correct'
              } else if (isCorrectOption) {
                reviewBadge = 'Answer'
              } else if (isWrongSelection) {
                reviewBadge = 'Your choice'
              }
            }

            return (
              <button
                key={key}
                type="button"
                onClick={() => {
                  if (isInteractive) {
                    onSelectOption?.(key)
                  }
                }}
                aria-pressed={isSelected}
                aria-disabled={!isInteractive}
                className={cn(
                  'question-option group',
                  !isInteractive && 'question-option--review',
                  hasOptionGraphics && 'question-option--has-graphics',
                  isGraphicOnlyOption && 'question-option--graphic-only',
                  isTextOnlyOption && 'question-option--text-only',
                  isMixedOption && 'question-option--mixed',
                  isInteractive &&
                    (isSelected
                      ? 'border-primary bg-primary/5 shadow-[0_10px_22px_rgba(88,204,2,0.08)]'
                      : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'),
                  mode === 'review' &&
                    isCorrectOption &&
                    'border-[#bfe698] bg-[#f5ffe8] shadow-[0_12px_24px_rgba(88,204,2,0.08)]',
                  mode === 'review' &&
                    isWrongSelection &&
                    'border-[#ffc2cd] bg-[#fff2f5] shadow-[0_12px_24px_rgba(255,107,130,0.08)]',
                  mode === 'review' &&
                    !isCorrectOption &&
                    !isWrongSelection &&
                    'border-slate-200 bg-white',
                )}
              >
                <div
                  className={cn(
                    'question-option__label',
                    isInteractive &&
                      (isSelected
                        ? 'bg-primary text-white'
                        : 'bg-slate-100 text-slate-500 group-hover:bg-slate-200'),
                    mode === 'review' &&
                      isCorrectOption &&
                      'bg-primary text-white',
                    mode === 'review' &&
                      isWrongSelection &&
                      'bg-[#ff7c94] text-white',
                    mode === 'review' &&
                      !isCorrectOption &&
                      !isWrongSelection &&
                      'bg-slate-100 text-slate-500',
                  )}
                >
                  {key}
                </div>
                <div className="question-option__content">
                  {reviewBadge && (
                    <span
                      className={cn(
                        'question-option__review-chip',
                        isCorrectOption
                          ? 'bg-[#e9f9d9] text-primary'
                          : 'bg-[#fff0f3] text-[#d95b73]',
                      )}
                    >
                      {reviewBadge}
                    </span>
                  )}
                  {hasOptionText && <span className="question-option__text">{optionText}</span>}
                  {option.graphics && option.graphics.length > 0 && (
                    <div className="question-option__media">
                      <div className="question-option__graphics">
                        {option.graphics.map((graphic) => (
                          <SvgGraphic
                            key={graphic.id}
                            graphic={graphic}
                            className="question-option__graphic-svg"
                            loadingFallback={
                              <div className="text-xs text-slate-400 italic">
                                [Loading image...]
                              </div>
                            }
                            fallback={
                              <div className="text-xs text-slate-400 italic">
                                [Image missing]
                              </div>
                            }
                          />
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {mode === 'interactive' && isSelected && (
                  <div className="question-option__check text-primary">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      width="20"
                      height="20"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  </div>
                )}
              </button>
            )
          })}
        </div>
      </section>
    </div>
  )
}
