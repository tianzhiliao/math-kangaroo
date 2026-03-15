import * as React from "react"
import { cn } from "../../lib/utils"
import { Menu, X } from "lucide-react"
import { Button } from "../ui/Button"

interface ExamLayoutProps {
  sidebar: React.ReactNode
  children: React.ReactNode
  className?: string
}

export function ExamLayout({ sidebar, children, className }: ExamLayoutProps) {
  const [isSidebarOpen, setIsSidebarOpen] = React.useState(false)

  return (
    <div
      className={cn(
        "min-h-screen bg-[radial-gradient(circle_at_top,_rgba(218,244,193,0.68),_#f6f8f4_48%,_#f3f4ef_100%)] flex flex-col xl:flex-row",
        className,
      )}
    >
      <div className="sticky top-0 z-20 flex items-center justify-between border-b border-white/80 bg-white/90 px-4 py-4 shadow-sm backdrop-blur xl:hidden">
        <span className="font-black text-lg tracking-[-0.03em] text-slate-900">Kangaroo Math</span>
        <Button variant="ghost" size="icon" onClick={() => setIsSidebarOpen(!isSidebarOpen)}>
          {isSidebarOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </Button>
      </div>

      <aside className="hidden h-screen shrink-0 border-r border-white/80 bg-white/90 backdrop-blur xl:sticky xl:top-0 xl:flex xl:w-[21rem] 2xl:w-[22.5rem]">
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden p-6">
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">{sidebar}</div>
        </div>
      </aside>

      {isSidebarOpen && (
        <div className="fixed inset-0 z-50 xl:hidden">
          <div
            className="absolute inset-0 bg-slate-900/20 backdrop-blur-sm transition-opacity"
            onClick={() => setIsSidebarOpen(false)}
          />
          <aside className="absolute bottom-0 right-0 top-0 flex w-full max-w-[22rem] flex-col bg-white shadow-2xl animate-in slide-in-from-right duration-300">
            <div className="flex min-h-0 flex-1 flex-col overflow-hidden p-6">
              <div className="mb-6 flex shrink-0 items-center justify-between border-b border-slate-100 pb-4">
                <span className="font-black text-lg tracking-[-0.03em] text-slate-900">Overview</span>
                <Button variant="ghost" size="icon" onClick={() => setIsSidebarOpen(false)}>
                  <X className="h-5 w-5" />
                </Button>
              </div>
              <div className="flex min-h-0 flex-1 flex-col overflow-hidden">{sidebar}</div>
            </div>
          </aside>
        </div>
      )}

      <main className="mx-auto w-full max-w-[920px] flex-1 p-4 md:p-6 xl:max-w-[1120px] xl:p-8 2xl:max-w-[1240px]">
        {children}
      </main>
    </div>
  )
}
