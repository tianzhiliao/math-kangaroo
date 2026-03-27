import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

/**
 * Persists practice answers across /practice/q/[n] navigations (same session).
 */
type PracticeAnswersState = {
  answers: Record<number, string>;
  lastVisitedQuestion: number | null;
  setAnswer: (globalOneBased: number, label: string) => void;
  setLastVisitedQuestion: (globalOneBased: number) => void;
  clear: () => void;
};

export const usePracticeAnswersStore = create<PracticeAnswersState>()(
  persist(
    (set) => ({
      answers: {},
      lastVisitedQuestion: null,
      setAnswer: (globalOneBased, label) =>
        set((s) => ({
          answers: { ...s.answers, [globalOneBased]: label },
        })),
      setLastVisitedQuestion: (globalOneBased) =>
        set({ lastVisitedQuestion: globalOneBased }),
      clear: () => set({ answers: {}, lastVisitedQuestion: null }),
    }),
    {
      name: "practice-progress-v1",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        answers: state.answers,
        lastVisitedQuestion: state.lastVisitedQuestion,
      }),
    },
  ),
);
