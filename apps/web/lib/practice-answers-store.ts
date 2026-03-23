import { create } from "zustand";

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

export const usePracticeAnswersStore = create<PracticeAnswersState>((set) => ({
  answers: {},
  lastVisitedQuestion: null,
  setAnswer: (globalOneBased, label) =>
    set((s) => ({
      answers: { ...s.answers, [globalOneBased]: label },
    })),
  setLastVisitedQuestion: (globalOneBased) =>
    set({ lastVisitedQuestion: globalOneBased }),
  clear: () => set({ answers: {}, lastVisitedQuestion: null }),
}));
