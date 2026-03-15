import { useEffect, useState } from 'react'
import { ArrowLeft, Medal, RotateCcw, Target } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Button } from '../components/ui/Button'
import { useExam } from '../context/ExamContext'
import { formatDuration } from '../lib/examSession'
import { getPracticeDoneRoute, type RestoreOutcome } from '../lib/resultPageRouting'
import { PRACTICE_EXAM_ID } from '../services/examService'

export default function PracticeDone() {
  const navigate = useNavigate()
  const [missingRestoreKey, setMissingRestoreKey] = useState<string | null>(null)
  const { currentExam, session, result, resumeExam, resetExam, startExam } = useExam()
  const restoreKey = PRACTICE_EXAM_ID
  const hasActivePracticeSession =
    currentExam?.paper_id === PRACTICE_EXAM_ID &&
    session?.examId === PRACTICE_EXAM_ID &&
    session.mode === 'practice'
  const restoreOutcome: RestoreOutcome = hasActivePracticeSession
    ? 'loaded'
    : missingRestoreKey === restoreKey
      ? 'missing'
      : 'restoring'

  useEffect(() => {
    if (hasActivePracticeSession) {
      return
    }

    let isCancelled = false

    void resumeExam(PRACTICE_EXAM_ID, 'practice', false).then((loaded) => {
      if (!isCancelled && !loaded) {
        setMissingRestoreKey(restoreKey)
      }
    })

    return () => {
      isCancelled = true
    }
  }, [hasActivePracticeSession, resumeExam, restoreKey])

  const routeState = getPracticeDoneRoute({
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

    if (routeState === 'toPractice') {
      navigate('/practice')
    }
  }, [navigate, routeState])

  if (routeState !== 'show' || !currentExam || !result) {
    return (
      <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(218,244,193,0.72),_#f6f8f4_55%,_#f3f4ef_100%)] px-4 py-8 md:px-8">
        <div className="mx-auto max-w-4xl animate-pulse space-y-4">
          <div className="h-48 rounded-[2rem] bg-white/80" />
          <div className="h-40 rounded-[2rem] bg-white/70" />
        </div>
      </div>
    )
  }

  const handleRestart = async () => {
    const started = await startExam(PRACTICE_EXAM_ID, 'practice')
    if (started) {
      navigate('/practice')
    }
  }

  const handleBackHome = () => {
    resetExam(PRACTICE_EXAM_ID, 'practice')
    navigate('/')
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(218,244,193,0.9),_#f6f8f4_52%,_#f3f4ef_100%)] px-4 py-6 md:px-8 md:py-8">
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
        <section className="rounded-[2.2rem] border border-white/80 bg-white/92 p-6 shadow-[0_24px_60px_rgba(122,151,92,0.14)] backdrop-blur md:p-8">
          <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-primary/10 px-4 py-2 text-[11px] font-black uppercase tracking-[0.28em] text-primary">
                  Practice Done
                </span>
                <span className="rounded-full bg-slate-100 px-4 py-2 text-[11px] font-black uppercase tracking-[0.28em] text-slate-500">
                  72 Questions
                </span>
              </div>
              <div className="space-y-2">
                <h1 className="text-4xl font-black tracking-[-0.05em] text-slate-950 md:text-5xl">
                  Clean finish.
                </h1>
                <p className="text-sm font-medium text-slate-500 md:text-base">
                  You checked every question in the practice bank.
                </p>
              </div>
            </div>

            <Button variant="outline" feedbackKind="nav" onClick={handleBackHome} className="self-start">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Home
            </Button>
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-3">
          <div className="rounded-[1.8rem] border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-[11px] font-black uppercase tracking-[0.24em] text-slate-400">
                  Score
                </div>
                <div className="mt-2 text-4xl font-black tracking-[-0.05em] text-slate-950">
                  {result.score}
                </div>
              </div>
              <div className="flex h-14 w-14 items-center justify-center rounded-[1.2rem] bg-[#eef8de] text-primary">
                <Medal className="h-6 w-6" />
              </div>
            </div>
          </div>
          <div className="rounded-[1.8rem] border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-[11px] font-black uppercase tracking-[0.24em] text-slate-400">
                  Correct
                </div>
                <div className="mt-2 text-4xl font-black tracking-[-0.05em] text-slate-950">
                  {result.correctCount}
                </div>
              </div>
              <div className="flex h-14 w-14 items-center justify-center rounded-[1.2rem] bg-[#e9f9d9] text-primary">
                <Target className="h-6 w-6" />
              </div>
            </div>
          </div>
          <div className="rounded-[1.8rem] border border-slate-200 bg-white p-5 shadow-sm">
            <div className="text-[11px] font-black uppercase tracking-[0.24em] text-slate-400">
              Time
            </div>
            <div className="mt-2 text-4xl font-black tracking-[-0.05em] text-slate-950">
              {formatDuration(result.elapsedSeconds)}
            </div>
          </div>
        </section>

        <section className="rounded-[2rem] border border-slate-200 bg-white p-5 shadow-sm md:p-6">
          <div className="flex flex-col gap-3 md:flex-row">
            <Button variant="primary" size="lg" fullWidth onClick={handleRestart}>
              <RotateCcw className="mr-2 h-4 w-4" />
              Practice Again
            </Button>
            <Button variant="outline" size="lg" fullWidth feedbackKind="nav" onClick={handleBackHome}>
              Back Home
            </Button>
          </div>
        </section>
      </div>
    </div>
  )
}
