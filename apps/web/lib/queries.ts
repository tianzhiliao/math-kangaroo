"use client";

import { useQuery } from "@tanstack/react-query";
import type { Exam, Manifest, PracticeBankResponse } from "./types";

export function useManifest() {
  return useQuery({
    queryKey: ["manifest"],
    queryFn: async () => {
      const r = await fetch("/api/exams");
      if (!r.ok) throw new Error("bad");
      return r.json() as Promise<Manifest>;
    },
  });
}

export function usePracticeBank() {
  return useQuery({
    queryKey: ["practice-bank"],
    queryFn: async () => {
      const r = await fetch("/api/practice-bank");
      if (!r.ok) throw new Error("bad");
      return r.json() as Promise<PracticeBankResponse>;
    },
  });
}

export function useExam(examId: string | undefined) {
  return useQuery({
    queryKey: ["exam", examId],
    queryFn: async () => {
      const r = await fetch(`/api/exams/${encodeURIComponent(examId!)}`);
      if (!r.ok) throw new Error("bad");
      return r.json() as Promise<Exam>;
    },
    enabled: !!examId,
  });
}
