import { useMemo, useState } from 'react'
import { ArrowRight, Clock3, PencilRuler } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useExam } from '../context/ExamContext'
import { PRACTICE_EXAM_ID } from '../services/examService'

export default function Home() {
  const navigate = useNavigate()
  const { getSavedPracticeResumeSummary, startExam, isLoading, error } = useExam()
  const [isStartingPractice, setIsStartingPractice] = useState(false)
  const practiceResumeSummary = useMemo(
    () => getSavedPracticeResumeSummary(),
    [getSavedPracticeResumeSummary],
  )
  const isResumingPractice = practiceResumeSummary !== null

  const handlePracticeStart = async () => {
    if (isResumingPractice) {
      navigate('/practice')
      return
    }

    setIsStartingPractice(true)
    const started = await startExam(PRACTICE_EXAM_ID, 'practice')
    setIsStartingPractice(false)

    if (started) {
      navigate('/practice')
    }
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(212,255,179,0.95),_rgba(249,251,247,0.92)_42%,_#f5f7f2_100%)] px-4 py-6 md:px-8 md:py-8">
      <div className="mx-auto flex min-h-[calc(100vh-3rem)] w-full max-w-5xl flex-col gap-8 rounded-[2.4rem] border border-white/80 bg-white/88 p-6 shadow-[0_28px_80px_rgba(122,151,92,0.14)] backdrop-blur md:p-8">
        <div className="space-y-3">
          <span className="inline-flex rounded-full bg-primary/10 px-4 py-2 text-xs font-black uppercase tracking-[0.34em] text-primary">
            Kangaroo Math
          </span>
          <h1 className="max-w-2xl text-4xl font-black tracking-[-0.05em] text-slate-950 md:text-6xl">
            Practice or exam.
          </h1>
        </div>

        {error && (
          <div className="mt-6 rounded-[1.6rem] border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-600">
            {error}
          </div>
        )}

        <div className="grid gap-4 py-8 md:grid-cols-2 md:py-10">
          <button
            type="button"
            onClick={handlePracticeStart}
            disabled={isLoading}
            className="group flex min-h-[18rem] flex-col justify-between rounded-[2rem] border border-[#d8eebf] bg-[linear-gradient(180deg,_#f5ffe8_0%,_#edf8dc_100%)] p-6 text-left shadow-[0_16px_34px_rgba(88,204,2,0.11)] transition-transform duration-200 hover:-translate-y-1 disabled:cursor-wait disabled:opacity-70 md:min-h-[22rem]"
          >
            <div className="space-y-4">
              <span className="inline-flex rounded-full bg-white/90 px-4 py-2 text-[11px] font-black uppercase tracking-[0.28em] text-primary shadow-sm">
                {isResumingPractice ? 'Continue Practice' : 'Practice'}
              </span>
              <div className="space-y-2">
                <h2 className="text-3xl font-black tracking-[-0.04em] text-slate-950 md:text-4xl">
                  {isResumingPractice
                    ? 'Pick up where you left off.'
                    : 'Learn one question at a time.'}
                </h2>
                <p className="max-w-sm text-sm font-medium leading-6 text-slate-600">
                  {isResumingPractice
                    ? `${practiceResumeSummary.checkedCount} checked · resume at question ${practiceResumeSummary.currentQuestionNumber}.`
                    : 'Untimed. Check each answer right away.'}
                </p>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="inline-flex items-center gap-2 rounded-full bg-white/80 px-4 py-2 text-sm font-bold text-slate-700">
                <PencilRuler className="h-4 w-4 text-primary" />
                72 questions
              </span>
              <span className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-primary text-white shadow-[0_8px_18px_rgba(88,204,2,0.26)] transition-transform duration-200 group-hover:translate-x-1">
                <ArrowRight className="h-5 w-5" />
              </span>
            </div>
            <span className="sr-only">
              {isStartingPractice
                ? 'Opening practice'
                : isResumingPractice
                  ? 'Continue practice'
                  : 'Open practice'}
            </span>
          </button>

          <button
            type="button"
            onClick={() => navigate('/exam')}
            className="group flex min-h-[18rem] flex-col justify-between rounded-[2rem] border border-slate-200 bg-[linear-gradient(180deg,_#ffffff_0%,_#f5f7fb_100%)] p-6 text-left shadow-[0_16px_34px_rgba(148,163,184,0.1)] transition-transform duration-200 hover:-translate-y-1 md:min-h-[22rem]"
          >
            <div className="space-y-4">
              <span className="inline-flex rounded-full bg-slate-100 px-4 py-2 text-[11px] font-black uppercase tracking-[0.28em] text-slate-600 shadow-sm">
                Exam
              </span>
              <div className="space-y-2">
                <h2 className="text-3xl font-black tracking-[-0.04em] text-slate-950 md:text-4xl">
                  Take a full paper.
                </h2>
                <p className="max-w-sm text-sm font-medium leading-6 text-slate-600">
                  Timed. Official scoring. Pick the year next.
                </p>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="inline-flex items-center gap-2 rounded-full bg-white px-4 py-2 text-sm font-bold text-slate-700 shadow-sm">
                <Clock3 className="h-4 w-4 text-slate-500" />
                45 minutes
              </span>
              <span className="inline-flex h-12 w-12 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-700 shadow-sm transition-transform duration-200 group-hover:translate-x-1">
                <ArrowRight className="h-5 w-5" />
              </span>
            </div>
          </button>
        </div>
      </div>
    </div>
  )
}
