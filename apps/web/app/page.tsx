import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-[100dvh] flex-col">
      <header className="px-6 pt-6 sm:px-8 sm:pt-8">
        <h1 className="max-w-xl text-balance text-left text-2xl font-black tracking-tight text-slate-900 sm:text-3xl">
          Exam prep for Math Kangaroo
        </h1>
      </header>
      <div className="flex flex-1 flex-col items-center justify-center gap-10 px-6 pb-12 pt-8">
        <div className="grid w-full max-w-md gap-6">
          <Link
            href="/exam"
            className="tap-target rounded-3xl bg-blue-500 py-8 text-center text-2xl font-black text-white shadow-lg shadow-blue-500/30 active:scale-[0.98]"
          >
            Start Exam
          </Link>
          <Link
            href="/practice"
            className="tap-target rounded-3xl bg-emerald-500 py-8 text-center text-2xl font-black text-white shadow-lg shadow-emerald-500/30 active:scale-[0.98]"
          >
            Practice
          </Link>
        </div>
      </div>
    </main>
  );
}
