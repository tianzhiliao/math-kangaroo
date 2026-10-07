"use client";

import { generatedAssetUrl } from "@/lib/asset-url";
import type { AssetRecord, GeneratedQuestion } from "@/lib/types";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { QuestionCard } from "./QuestionCard";

function svgAssets(assets: AssetRecord[]): AssetRecord[] {
  return assets.filter(
    (asset) =>
      asset.path.endsWith(".svg") &&
      asset.path !== "compare.png" &&
      asset.path !== "card.png" &&
      !asset.path.endsWith("/compare.png") &&
      !asset.path.endsWith("/card.png"),
  );
}

export function GeneratedQuestionSection({
  examId,
  questionId,
}: {
  examId: string;
  questionId: string;
}) {
  const { data } = useQuery({
    queryKey: ["generated-question", examId, questionId],
    queryFn: async (): Promise<GeneratedQuestion | null> => {
      const response = await fetch(
        `/api/generated/${encodeURIComponent(examId)}/${encodeURIComponent(questionId)}`,
      );
      if (!response.ok) return null;
      const body: unknown = await response.json();
      if (!body || typeof body !== "object") return null;
      return body as GeneratedQuestion;
    },
    retry: false,
  });

  const questionKey = `${examId}/${questionId}`;
  const [openKey, setOpenKey] = useState<string | null>(null);
  const open = openKey === questionKey;

  if (!data) return null;

  const assets = svgAssets(data.assets);

  return (
    <section
      aria-label="变式题"
      className="mx-auto mt-5 w-full max-w-4xl border-t-2 border-dashed border-violet-300 pt-4"
    >
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpenKey(open ? null : questionKey)}
        className="inline-flex min-h-[44px] items-center rounded-xl border-2 border-violet-300 bg-violet-50 px-4 text-base font-black text-violet-950 transition hover:border-violet-400 hover:bg-violet-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:ring-offset-2"
      >
        变式题
      </button>
      {open ? (
        <div className="mt-3">
          <QuestionCard
            examId={examId}
            question={data}
            allAssets={assets}
            selectedLabel={null}
            onSelect={() => {}}
            disabled={false}
            readOnly
            hideAudio
            showOutcome={false}
            correctLabel=""
            resolveAssetUrl={(asset) =>
              generatedAssetUrl(examId, questionId, asset.path)
            }
          />
        </div>
      ) : null}
    </section>
  );
}
