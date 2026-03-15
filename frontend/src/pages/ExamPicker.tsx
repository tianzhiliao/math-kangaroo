import { useEffect, useState } from 'react'
import { ArrowLeft, ArrowRight, Clock3, PencilRuler } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Button } from '../components/ui/Button'
import { useExam } from '../context/ExamContext'
import { getAllExams } from '../services/examService'

export default function ExamPicker() {
  const navigate = useNavigate()
  const { startExam, isLoading, error } = useExam()
  const [exams, setExams] = useState<string[]>([])
  const [startingExamId, setStartingExamId] = useState<string | null>(null)

  useEffect(() => {
    const loadExams = async () => {
      const examIds = await getAllExams()
      setExams(examIds)
    }

    void loadExams()
  }, [])

  const handleStartExam = async (examId: string) => {
    setStartingExamId(examId)
    const started = await startExam(examId, 'real')
    setStartingExamId(null)

    if (started) {
      navigate(`/exam/${examId}`)
    }
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(218,244,193,0.72),_#f6f8f4_55%,_#f3f4ef_100%)] px-4 py-6 md:px-8 md:py-8">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
        <section className="rounded-[2.2rem] border border-white/80 bg-white/88 p-6 shadow-[0_22px_60px_rgba(122,151,92,0.14)] backdrop-blur md:p-8">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-3">
              <Button variant="outline" feedbackKind="nav" onClick={() => navigate('/')}>
                <ArrowLeft className="mr-2 h-4 w-4" />
                Home
              </Button>
              <span className="inline-flex rounded-full bg-slate-100 px-4 py-2 text-[11px] font-black uppercase tracking-[0.28em] text-slate-600">
                Real Exam
              </span>
            </div>
            <h1 className="text-4xl font-black tracking-[-0.05em] text-slate-950 md:text-5xl">
              Pick a paper.
            </h1>
          </div>
        </section>

        {error && (
          <div className="rounded-[1.5rem] border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-600">
            {error}
          </div>
        )}

        <div className="grid gap-4 md:grid-cols-2">
          {exams.map((examId) => {
            const year = examId.replace('Exam_', '')
            const isStarting = startingExamId === examId

            return (
              <article
                key={examId}
                className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-[0_16px_34px_rgba(148,163,184,0.1)]"
              >
                <div className="flex h-full flex-col gap-6">
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-2">
                      <p className="text-xs font-black uppercase tracking-[0.32em] text-primary">
                        Exam {year}
                      </p>
                      <h2 className="text-3xl font-black tracking-[-0.04em] text-slate-950">
                        {year}
                      </h2>
                    </div>
                    <span className="rounded-full bg-primary/10 px-4 py-2 text-sm font-black text-primary">
                      Grade 1-2
                    </span>
                  </div>

                  <div className="flex flex-wrap gap-3">
                    <span className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-4 py-2 text-sm font-bold text-slate-700">
                      <Clock3 className="h-4 w-4 text-slate-500" />
                      45 min
                    </span>
                    <span className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-4 py-2 text-sm font-bold text-slate-700">
                      <PencilRuler className="h-4 w-4 text-slate-500" />
                      18 questions
                    </span>
                  </div>

                  <Button
                    variant="primary"
                    size="lg"
                    fullWidth
                    onClick={() => handleStartExam(examId)}
                    disabled={isLoading}
                    className="justify-between px-6"
                  >
                    <span>{isStarting ? 'Starting...' : 'Start Exam'}</span>
                    <ArrowRight className="h-5 w-5" />
                  </Button>
                </div>
              </article>
            )
          })}
        </div>
      </div>
    </div>
  )
}
