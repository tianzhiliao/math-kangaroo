import { create } from "zustand";

/**
 * Persists practice answers across /practice/q/[n] navigations (same session).
 */
type PracticeAnswersState = {
  answers: Record<number, string>;
  setAnswer: (globalOneBased: number, label: string) => void;
  clear: () => void;
};

export const usePracticeAnswersStore = create<PracticeAnswersState>((set) => ({
  answers: {},
  setAnswer: (globalOneBased, label) =>
    set((s) => ({
      answers: { ...s.answers, [globalOneBased]: label },
    })),
  clear: () => set({ answers: {} }),
}));
