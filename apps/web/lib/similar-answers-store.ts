import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

/**
 * Answers to the similar questions, keyed by `${examId}/${questionId}` of the
 * source question. Kept apart from practice progress so a similar question
 * never changes the paper's score.
 */
type SimilarAnswersState = {
  answers: Record<string, string>;
  setAnswer: (key: string, label: string) => void;
  reset: (key: string) => void;
};

export const useSimilarAnswersStore = create<SimilarAnswersState>()(
  persist(
    (set) => ({
      answers: {},
      setAnswer: (key, label) =>
        set((s) => ({ answers: { ...s.answers, [key]: label } })),
      reset: (key) =>
        set((s) => {
          const answers = { ...s.answers };
          delete answers[key];
          return { answers };
        }),
    }),
    {
      name: "similar-answers-v1",
      storage: createJSONStorage(() => localStorage),
    },
  ),
);
