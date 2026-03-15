import { useEffect, useState } from 'react'
import { ArrowLeft, Clock3, Medal, RotateCcw, Target } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'
import { QuestionCard } from '../components/exam/QuestionCard'
import { QuestionNavigation } from '../components/exam/QuestionNavigation'
import { Button } from '../components/ui/Button'
import { useExam } from '../context/ExamContext'
import { formatDuration } from '../lib/examSession'
import { getQuestionAudioTarget } from '../lib/questionIdentity'
import { getReportRoute, type RestoreOutcome } from '../lib/resultPageRouting'
import type { QuestionStatus } from '../types/examSession'

function getHeadline(accuracy: number) {
  if (accuracy >= 85) {
    return 'Excellent focus.'
  }

  if (accuracy >= 60) {
    return 'Solid work.'
  }

  return 'Review and reset.'
}

export default function Report() {
  const navigate = useNavigate()
  const { examId } = useParams<{ examId: string }>()
  const [selectedQuestionIndex, setSelectedQuestionIndex] = useState<number | null>(null)
  const [missingRestoreKey, setMissingRestoreKey] = useState<string | null>(null)
  const { currentExam, session, result, resumeExam, resetExam, startExam } = useExam()
  const restoreKey = examId ?? 'report'
  const hasActiveReportSession =
    examId !== undefined &&
    currentExam?.paper_id === examId &&
    session?.examId === examId &&
    session.mode === 'real'
  const restoreOutcome: RestoreOutcome = hasActiveReportSession
    ? 'loaded'
    : missingRestoreKey === restoreKey
      ? 'missing'
      : 'restoring'

  useEffect(() => {
    if (!examId) {
      navigate('/')
      return
    }

    if (hasActiveReportSession) {
      return
    }

    let isCancelled = false

    void resumeExam(examId, 'real', false).then((loaded) => {
      if (!isCancelled && !loaded) {
        setMissingRestoreKey(restoreKey)
      }
    })

    return () => {
      isCancelled = true
    }
  }, [examId, hasActiveReportSession, navigate, restoreKey, resumeExam])

  const routeState = getReportRoute({
    restoreOutcome,
    hasCurrentExam: currentExam !== null,
    hasSession: session !== null,
    sessionMode: session?.mode ?? null,
    isSubmitted: session ? session.submittedAt !== null : false,
    hasResult: result !== null,
  })

  useEffect(() => {
    if (routeState === 'toHome') {
      navigate('/')
      return
    }

    if (routeState === 'toExam' && examId) {
      navigate(`/exam/${examId}`)
    }
  }, [examId, navigate, routeState])

  if (routeState !== 'show' || !currentExam || !result || !examId) {
    return (
      <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(218,244,193,0.72),_#f6f8f4_55%,_#f3f4ef_100%)] px-4 py-8 md:px-6">
        <div className="mx-auto max-w-6xl animate-pulse space-y-6">
          <div className="h-40 rounded-[2rem] bg-white/80" />
          <div className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
            <div className="h-[520px] rounded-[2rem] bg-white/80" />
            <div className="h-[520px] rounded-[2rem] bg-white/70" />
          </div>
        </div>
      </div>
    )
  }

  const firstReviewIndex = result.questionResults.findIndex(
    (questionResult) => questionResult.tone !== 'correct',
  )
  const activeSelectedIndex =
    selectedQuestionIndex !== null
      ? Math.min(selectedQuestionIndex, result.questionResults.length - 1)
      : firstReviewIndex >= 0
        ? firstReviewIndex
        : 0

  const reviewStatuses: QuestionStatus[] = result.questionResults.map((questionResult) => ({
    questionId: questionResult.questionId,
    questionIndex: questionResult.questionIndex,
    tone: questionResult.tone,
    isSelected: questionResult.questionIndex === activeSelectedIndex,
  }))
  const selectedQuestion = currentExam.questions[activeSelectedIndex]
  const selectedResult = result.questionResults[activeSelectedIndex]
  const headline = getHeadline(result.accuracy)

  const summaryCards = [
    {
      label: 'Score',
      value: result.scoreLabel,
      icon: Medal,
      tone: 'bg-[#eef8de] text-primary',
    },
    {
      label: 'Correct',
      value: `${result.correctCount}`,
      icon: Target,
      tone: 'bg-[#e9f9d9] text-primary',
    },
    {
      label: 'Time',
      value: formatDuration(result.elapsedSeconds),
      icon: Clock3,
      tone: 'bg-[#edf4ff] text-sky-700',
    },
  ]

  const handleRestart = async () => {
    const started = await startExam(examId, 'real')
    if (started) {
      navigate(`/exam/${examId}`)
    }
  }

  const handleBackHome = () => {
    resetExam(examId, 'real')
    navigate('/')
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(218,244,193,0.9),_#f6f8f4_52%,_#f3f4ef_100%)] px-4 py-6 md:px-8 md:py-8">
      <div className="mx-auto flex max-w-6xl flex-col gap-6">
        <section className="rounded-[2.2rem] border border-white/80 bg-white/92 p-6 shadow-[0_24px_60px_rgba(122,151,92,0.14)] backdrop-blur md:p-8">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-primary/10 px-4 py-2 text-[11px] font-black uppercase tracking-[0.28em] text-primary">
                  Real Exam Result
                </span>
                <span className="rounded-full bg-slate-100 px-4 py-2 text-[11px] font-black uppercase tracking-[0.28em] text-slate-500">
                  {currentExam.paper_id.replace('_', ' ')}
                </span>
              </div>
              <div className="space-y-2">
                <h1 className="text-4xl font-black tracking-[-0.05em] text-slate-950 md:text-5xl">
                  {headline}
                </h1>
                <p className="text-sm font-medium text-slate-500 md:text-base">
                  Tap any bubble to review that question.
                </p>
              </div>
            </div>

            <Button variant="outline" feedbackKind="nav" onClick={handleBackHome} className="self-start">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Home
            </Button>
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {summaryCards.map(({ label, value, icon: Icon, tone }) => (
              <div key={label} className="rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-[11px] font-black uppercase tracking-[0.24em] text-slate-400">
                      {label}
                    </div>
                    <div className="mt-2 text-4xl font-black tracking-[-0.05em] text-slate-950">
                      {value}
                    </div>
                  </div>
                  <div className={`flex h-14 w-14 items-center justify-center rounded-[1.2rem] ${tone}`}>
                    <Icon className="h-6 w-6" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        <div className="grid gap-6 lg:grid-cols-[0.88fr_1.12fr]">
          <aside className="space-y-4 rounded-[2rem] border border-slate-200 bg-white p-5 shadow-[0_18px_40px_rgba(15,23,42,0.06)]">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-2xl font-black tracking-[-0.04em] text-slate-950">
                  Question Map
                </h2>
                <p className="mt-1 text-sm font-medium text-slate-500">
                  Green is right. Pink is wrong.
                </p>
              </div>
              <Button variant="primary" onClick={handleRestart}>
                <RotateCcw className="mr-2 h-4 w-4" />
                Try Again
              </Button>
            </div>

            <div className="rounded-[1.5rem] border border-slate-200 bg-white p-3 shadow-sm">
              <QuestionNavigation
                items={reviewStatuses}
                variant="review"
                onNavigate={setSelectedQuestionIndex}
                className="w-full"
              />
            </div>
          </aside>

          <section className="space-y-4 rounded-[2rem] border border-slate-200 bg-white p-5 shadow-[0_18px_40px_rgba(15,23,42,0.06)]">
            <div className="rounded-[1.75rem] border border-slate-200 bg-slate-50 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-slate-950 px-3 py-1 text-[11px] font-black uppercase tracking-[0.28em] text-white">
                  Question {selectedResult.questionNumber}
                </span>
                <span
                  className={`rounded-full px-3 py-1 text-[11px] font-black uppercase tracking-[0.28em] ${
                    selectedResult.tone === 'correct'
                      ? 'bg-[#e9f9d9] text-primary'
                      : selectedResult.tone === 'incorrect'
                        ? 'bg-[#fff0f3] text-[#d95b73]'
                        : 'bg-[#fff8df] text-[#a77910]'
                  }`}
                >
                  {selectedResult.tone}
                </span>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-3">
                <div className="rounded-2xl bg-white p-4 shadow-sm">
                  <div className="text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">
                    Your Answer
                  </div>
                  <div className="mt-2 text-3xl font-black text-slate-950">
                    {selectedResult.userAnswer ?? 'None'}
                  </div>
                </div>
                <div className="rounded-2xl bg-white p-4 shadow-sm">
                  <div className="text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">
                    Correct
                  </div>
                  <div className="mt-2 text-3xl font-black text-primary">
                    {selectedResult.correctAnswer}
                  </div>
                </div>
                <div className="rounded-2xl bg-white p-4 shadow-sm">
                  <div className="text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">
                    Score
                  </div>
                  <div
                    className={`mt-2 text-3xl font-black ${
                      selectedResult.scoreDelta > 0
                        ? 'text-primary'
                        : selectedResult.scoreDelta < 0
                          ? 'text-[#d95b73]'
                          : 'text-slate-500'
                    }`}
                  >
                    {selectedResult.scoreDelta > 0 ? '+' : ''}
                    {selectedResult.scoreDelta}
                  </div>
                </div>
              </div>
            </div>

            <QuestionCard
              audioTarget={getQuestionAudioTarget(
                selectedQuestion,
                currentExam.paper_id,
                selectedResult.questionNumber,
              )}
              question={selectedQuestion}
              selectedOption={selectedResult.userAnswer}
              correctOption={selectedResult.correctAnswer}
              mode="review"
            />
          </section>
        </div>
      </div>
    </div>
  )
}
