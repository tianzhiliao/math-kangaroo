import { useEffect, useMemo, useState } from 'react'
import { ArrowRight, Check, LogOut, Sparkles } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { stopStemAudioPlayback } from '../audio/stemAudioController'
import { QuestionCard } from '../components/exam/QuestionCard'
import { QuestionNavigation } from '../components/exam/QuestionNavigation'
import { QuestionCardSkeleton } from '../components/exam/QuestionCardSkeleton'
import { ExamLayout } from '../components/layout/ExamLayout'
import { ActionConfirmDialog } from '../components/ui/ActionConfirmDialog'
import { Button } from '../components/ui/Button'
import { ProgressBar } from '../components/ui/ProgressBar'
import { useExam } from '../context/ExamContext'
import { hasMeaningfulPracticeProgress } from '../lib/examSession'
import {
  getQuestionAudioTarget,
  getQuestionSessionId,
  getQuestionSourceLabel,
} from '../lib/questionIdentity'
import { PRACTICE_EXAM_ID } from '../services/examService'

function getNextOpenIndex(items: { tone: string; questionIndex: number }[], currentIndex: number) {
  const nextOpen = items.find(
    (item) => item.questionIndex > currentIndex && item.tone === 'unanswered',
  )
  if (nextOpen) {
    return nextOpen.questionIndex
  }

  const firstOpen = items.find((item) => item.tone === 'unanswered')
  return firstOpen?.questionIndex ?? null
}

export default function Practice() {
  const navigate = useNavigate()
  const [isExitDialogOpen, setIsExitDialogOpen] = useState(false)
  const {
    currentExam,
    session,
    currentQuestionIndex,
    answers,
    submittedQuestions,
    submittedCount,
    isPracticeComplete,
    isSubmitted,
    isLoading,
    error,
    questionStatuses,
    resumeExam,
    selectAnswer,
    submitQuestion,
    nextQuestion,
    prevQuestion,
    jumpToQuestion,
    submitExam,
    resetExam,
  } = useExam()

  useEffect(() => {
    let isCancelled = false

    void resumeExam(PRACTICE_EXAM_ID, 'practice', true).then((loaded) => {
      if (!loaded && !isCancelled) {
        navigate('/')
      }
    })

    return () => {
      isCancelled = true
    }
  }, [navigate, resumeExam])

  useEffect(() => {
    if (isSubmitted) {
      navigate('/practice/done')
    }
  }, [isSubmitted, navigate])

  useEffect(() => {
    return () => {
      stopStemAudioPlayback()
    }
  }, [])

  const currentQuestion = currentExam?.questions[currentQuestionIndex]
  const currentQuestionSessionId = currentQuestion ? getQuestionSessionId(currentQuestion) : null
  const selectedOption =
    currentQuestion && currentQuestionSessionId !== null
      ? answers[currentQuestionSessionId] ?? null
      : null
  const isCurrentSubmitted = currentQuestion
    ? submittedQuestions.includes(getQuestionSessionId(currentQuestion))
    : false

  const correctCount = useMemo(
    () => questionStatuses.filter((status) => status.tone === 'correct').length,
    [questionStatuses],
  )
  const hasProgress = hasMeaningfulPracticeProgress(session)

  const handleExitIntent = () => {
    stopStemAudioPlayback()

    if (!hasProgress) {
      resetExam(PRACTICE_EXAM_ID, 'practice')
      navigate('/')
      return
    }

    setIsExitDialogOpen(true)
  }

  const handleKeepProgressExit = () => {
    setIsExitDialogOpen(false)
    navigate('/')
  }

  const handleDiscardProgressExit = () => {
    setIsExitDialogOpen(false)
    resetExam(PRACTICE_EXAM_ID, 'practice')
    navigate('/')
  }

  if (error) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-slate-50 p-4">
        <div className="text-xl font-bold text-rose-500">Unable to load practice</div>
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
            <div className="flex-1 rounded-[1.75rem] bg-slate-100" />
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

  const nextOpenIndex = getNextOpenIndex(questionStatuses, currentQuestionIndex)
  const sourceLabel = getQuestionSourceLabel(currentQuestion)

  const sidebar = (
    <div className="grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)] gap-4 overflow-hidden">
      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-primary/10 px-3 py-1 text-[11px] font-black uppercase tracking-[0.28em] text-primary">
            Practice
          </span>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-[11px] font-black uppercase tracking-[0.28em] text-slate-500">
            72 Questions
          </span>
        </div>
        <div className="rounded-[1.65rem] border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-end justify-between gap-3">
            <div>
              <div className="text-xs font-black uppercase tracking-[0.24em] text-slate-400">
                Checked
              </div>
              <div className="mt-1 text-3xl font-black tracking-[-0.05em] text-slate-950">
                {submittedCount}
                <span className="ml-1 text-lg font-bold text-slate-400">/ {currentExam.questions.length}</span>
              </div>
            </div>
            <div className="rounded-2xl bg-[#eef8de] px-4 py-3 text-right">
              <div className="text-[11px] font-black uppercase tracking-[0.24em] text-primary/70">
                Correct
              </div>
              <div className="text-2xl font-black text-primary">{correctCount}</div>
            </div>
          </div>
          <ProgressBar current={submittedCount} total={currentExam.questions.length} className="mt-4" />
        </div>
      </div>

      <div className="min-h-0 overflow-y-auto rounded-[1.75rem] border border-slate-200 bg-white p-3 shadow-sm">
        <QuestionNavigation
          items={questionStatuses}
          onNavigate={jumpToQuestion}
          variant="practice"
          className="w-full"
        />
      </div>
    </div>
  )

  return (
    <ExamLayout sidebar={sidebar}>
      <section className="mb-4 rounded-[2rem] border border-white/80 bg-white/92 p-4 shadow-[0_18px_44px_rgba(122,151,92,0.08)] backdrop-blur md:p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-primary/10 px-3 py-1 text-[11px] font-black uppercase tracking-[0.28em] text-primary">
              Practice
            </span>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-[11px] font-black uppercase tracking-[0.28em] text-slate-500">
              Question {currentQuestionIndex + 1} / {currentExam.questions.length}
            </span>
            {sourceLabel && (
              <span className="rounded-full bg-[#eef4ff] px-3 py-1 text-[11px] font-black uppercase tracking-[0.22em] text-slate-500">
                {sourceLabel}
              </span>
            )}
          </div>

          <Button variant="outline" feedbackKind="nav" onClick={handleExitIntent} className="self-start">
            <LogOut className="mr-2 h-4 w-4" />
            Exit
          </Button>
        </div>
      </section>

      <ActionConfirmDialog
        open={isExitDialogOpen}
        accentLabel="Leave Practice"
        title="Keep this practice for later?"
        description="You can leave now and continue from the same question later, or discard this run and start fresh next time."
        primaryLabel="Leave and keep progress"
        secondaryLabel="Discard progress"
        tertiaryLabel="Stay here"
        onPrimary={handleKeepProgressExit}
        onSecondary={handleDiscardProgressExit}
        onTertiary={() => setIsExitDialogOpen(false)}
      />

      <QuestionCard
        audioTarget={getQuestionAudioTarget(
          currentQuestion,
          currentExam.paper_id,
          currentQuestionIndex + 1,
        )}
        question={currentQuestion}
        selectedOption={selectedOption}
        onSelectOption={(optionKey) => {
          if (currentQuestionSessionId !== null) {
            selectAnswer(currentQuestionSessionId, optionKey)
          }
        }}
        mode={isCurrentSubmitted ? 'review' : 'interactive'}
        correctOption={isCurrentSubmitted ? currentQuestion.answer : undefined}
        className="mb-5"
      />

      {isCurrentSubmitted && (
        <section className="mb-5 rounded-[1.75rem] border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-center gap-3">
            <span
              className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-black ${
                selectedOption === currentQuestion.answer
                  ? 'bg-[#e9f9d9] text-primary'
                  : 'bg-[#fff0f3] text-[#d95b73]'
              }`}
            >
              <Sparkles className="h-4 w-4" />
              {selectedOption === currentQuestion.answer ? 'Nice work.' : 'Not this one.'}
            </span>
            <span className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-4 py-2 text-sm font-bold text-slate-700">
              Correct answer {currentQuestion.answer}
            </span>
          </div>
        </section>
      )}

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

          <div className="flex w-full flex-col gap-3 lg:w-auto lg:flex-row">
            <Button
              variant="outline"
              feedbackKind="nav"
              onClick={() => {
                if (currentQuestionIndex === currentExam.questions.length - 1 && nextOpenIndex !== null) {
                  jumpToQuestion(nextOpenIndex)
                  return
                }
                nextQuestion()
              }}
              disabled={
                currentQuestionIndex === currentExam.questions.length - 1 && nextOpenIndex === null
              }
              className="w-full lg:w-32"
            >
              Next
            </Button>
            <Button
              variant="primary"
              feedbackKind={isCurrentSubmitted ? 'nav' : 'primary'}
              onClick={() => {
                if (!isCurrentSubmitted) {
                  if (currentQuestionSessionId !== null) {
                    submitQuestion(currentQuestionSessionId)
                  }
                  return
                }

                if (isPracticeComplete) {
                  stopStemAudioPlayback()
                  submitExam('practice_finish')
                  return
                }

                if (currentQuestionIndex === currentExam.questions.length - 1 && nextOpenIndex !== null) {
                  jumpToQuestion(nextOpenIndex)
                  return
                }

                nextQuestion()
              }}
              disabled={!isCurrentSubmitted && !selectedOption}
              className="w-full lg:min-w-44"
            >
              {!isCurrentSubmitted
                ? 'Check'
                : isPracticeComplete
                  ? 'See Summary'
                  : 'Next'}
              {isCurrentSubmitted && <ArrowRight className="ml-2 h-4 w-4" />}
              {!isCurrentSubmitted && <Check className="ml-2 h-4 w-4" />}
            </Button>
          </div>
        </div>
      </section>
    </ExamLayout>
  )
}
