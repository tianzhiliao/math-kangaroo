import { useEffect } from 'react'
import { AlertTriangle, ArrowLeft, Clock3 } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'
import { stopStemAudioPlayback } from '../audio/stemAudioController'
import { QuestionCard } from '../components/exam/QuestionCard'
import { QuestionNavigation } from '../components/exam/QuestionNavigation'
import { QuestionCardSkeleton } from '../components/exam/QuestionCardSkeleton'
import { ExamLayout } from '../components/layout/ExamLayout'
import { Button } from '../components/ui/Button'
import { ProgressBar } from '../components/ui/ProgressBar'
import { useExam } from '../context/ExamContext'
import { formatDuration } from '../lib/examSession'
import { getQuestionAudioTarget, getQuestionSessionId } from '../lib/questionIdentity'

function getTimerClassName(remainingSeconds: number | null) {
  if (remainingSeconds === null) {
    return 'border-slate-200 bg-white text-slate-700'
  }

  if (remainingSeconds <= 180) {
    return 'border-[#ffc2cd] bg-[#fff2f5] text-[#d95b73] shadow-[0_14px_26px_rgba(255,107,130,0.12)]'
  }

  if (remainingSeconds <= 600) {
    return 'border-[#f6dd89] bg-[#fff9e7] text-[#a77910] shadow-[0_14px_26px_rgba(255,200,0,0.12)]'
  }

  return 'border-[#cfe8ae] bg-[#f5ffe8] text-[#4d8e1a]'
}

export default function Exam() {
  const navigate = useNavigate()
  const { examId } = useParams<{ examId: string }>()
  const {
    currentExam,
    currentQuestionIndex,
    answers,
    remainingSeconds,
    answeredCount,
    canSubmit,
    isSubmitted,
    isLoading,
    error,
    questionStatuses,
    resumeExam,
    selectAnswer,
    nextQuestion,
    prevQuestion,
    jumpToQuestion,
    submitExam,
  } = useExam()

  useEffect(() => {
    if (!examId) {
      navigate('/')
      return
    }

    let isCancelled = false

    void resumeExam(examId, 'real', true).then((loaded) => {
      if (!loaded && !isCancelled) {
        navigate('/')
      }
    })

    return () => {
      isCancelled = true
    }
  }, [examId, navigate, resumeExam])

  useEffect(() => {
    if (examId && isSubmitted) {
      navigate(`/report/${examId}`)
    }
  }, [examId, isSubmitted, navigate])

  useEffect(() => {
    return () => {
      stopStemAudioPlayback()
    }
  }, [])

  const currentQuestion = currentExam?.questions[currentQuestionIndex]
  const currentQuestionSessionId = currentQuestion ? getQuestionSessionId(currentQuestion) : null
  const timerLabel = formatDuration(remainingSeconds ?? 0)

  if (error) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-slate-50 p-4">
        <div className="text-xl font-bold text-rose-500">Unable to load exam</div>
        <div className="text-slate-600">{error}</div>
        <Button variant="primary" onClick={() => navigate('/')}>
          Back Home
        </Button>
      </div>
    )
  }

  if (isLoading || !currentExam || !currentQuestion) {
    return (
      <ExamLayout
        sidebar={
          <div className="flex h-full flex-col gap-4 animate-pulse">
            <div className="h-8 w-1/2 rounded bg-slate-200" />
            <div className="h-24 rounded-3xl bg-slate-100" />
            <div className="h-[20rem] rounded-[1.75rem] bg-slate-100" />
          </div>
        }
      >
        <div className="mb-8 flex flex-col gap-4 animate-pulse">
          <div className="h-10 w-1/2 rounded bg-slate-200" />
          <div className="h-4 w-full rounded bg-slate-100" />
        </div>
        <QuestionCardSkeleton />
      </ExamLayout>
    )
  }

  const sidebar = (
    <div className="grid h-full min-h-0 grid-rows-[auto_1fr_auto] gap-4 overflow-hidden">
      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-primary/10 px-3 py-1 text-[11px] font-black uppercase tracking-[0.28em] text-primary">
            Real Exam
          </span>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-[11px] font-black uppercase tracking-[0.28em] text-slate-500">
            {currentExam.paper_id.replace('_', ' ')}
          </span>
        </div>
        <div className="rounded-[1.65rem] border border-slate-200 bg-white p-4 shadow-sm">
          <div>
            <div className="text-xs font-black uppercase tracking-[0.24em] text-slate-400">
              Answered
            </div>
            <div className="mt-1 text-3xl font-black tracking-[-0.05em] text-slate-950">
              {answeredCount}
              <span className="ml-1 text-lg font-bold text-slate-400">/ {currentExam.questions.length}</span>
            </div>
          </div>
          <ProgressBar current={answeredCount} total={currentExam.questions.length} className="mt-4" />
        </div>
      </div>

      <div className="rounded-[1.75rem] border border-slate-200 bg-white p-3 shadow-sm">
        <QuestionNavigation
          items={questionStatuses}
          onNavigate={jumpToQuestion}
          variant="real"
          className="w-full"
        />
      </div>

      <div className="space-y-3 border-t border-slate-100 pt-4">
        <Button
          variant="primary"
          fullWidth
          disabled={!canSubmit}
          onClick={() => {
            stopStemAudioPlayback()
            submitExam('manual')
          }}
          className="justify-center"
        >
          Submit Exam
        </Button>
        {!canSubmit && (
          <p className="text-center text-xs font-semibold text-slate-400">
            Answer all {currentExam.questions.length} questions first.
          </p>
        )}
      </div>
    </div>
  )

  return (
    <ExamLayout sidebar={sidebar}>
      <section className="mb-4 rounded-[2rem] border border-white/80 bg-white/92 p-4 shadow-[0_18px_44px_rgba(122,151,92,0.08)] backdrop-blur md:p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" feedbackKind="nav" onClick={() => navigate('/exam')}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Papers
            </Button>
            <span className="rounded-full bg-primary/10 px-3 py-1 text-[11px] font-black uppercase tracking-[0.28em] text-primary">
              Real Exam
            </span>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-[11px] font-black uppercase tracking-[0.28em] text-slate-500">
              Question {currentQuestionIndex + 1} / {currentExam.questions.length}
            </span>
          </div>

          <div
            className={`inline-flex items-center gap-2 self-start rounded-[1.3rem] border px-4 py-3 text-lg font-black ${getTimerClassName(
              remainingSeconds,
            )}`}
          >
            {(remainingSeconds ?? 0) <= 600 ? (
              <AlertTriangle className="h-5 w-5" />
            ) : (
              <Clock3 className="h-5 w-5" />
            )}
            {timerLabel}
          </div>
        </div>
      </section>

      <QuestionCard
        audioTarget={getQuestionAudioTarget(
          currentQuestion,
          currentExam.paper_id,
          currentQuestionIndex + 1,
        )}
        question={currentQuestion}
        selectedOption={
          currentQuestionSessionId !== null ? answers[currentQuestionSessionId] ?? null : null
        }
        onSelectOption={(optionKey) => {
          if (currentQuestionSessionId !== null) {
            selectAnswer(currentQuestionSessionId, optionKey)
          }
        }}
        className="mb-5"
      />

      <section className="rounded-[1.75rem] border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <Button
            variant="outline"
            feedbackKind="nav"
            onClick={prevQuestion}
            disabled={currentQuestionIndex === 0}
            className="w-full lg:w-32"
          >
            Previous
          </Button>
          <Button
            variant="outline"
            feedbackKind="nav"
            onClick={nextQuestion}
            disabled={currentQuestionIndex === currentExam.questions.length - 1}
            className="w-full lg:w-32"
          >
            Next
          </Button>
        </div>
      </section>
    </ExamLayout>
  )
}
