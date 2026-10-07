"use client";

import { generatedAssetUrl } from "@/lib/asset-url";
import type { AssetRecord, GeneratedQuestion } from "@/lib/types";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { QuestionCard } from "./QuestionCard";
import { Button } from "@/components/ui/Button";

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

  const toggle = (
    <Button
      variant={open ? "outline" : "primary"}
      aria-expanded={open}
      onClick={() => setOpenKey(open ? null : questionKey)}
      className={open ? "border-transparent" : ""}
    >
      {open ? "Close" : "Open"}
    </Button>
  );

  return (
    <section
      aria-label="变式题"
      className="w-full rounded-panel bg-mk-series-level-p px-5 py-5 md:px-6"
    >
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <p className="text-meta text-mk-ink-60">变式题</p>
          <h2 className="mt-0.5 text-h5">
            Try a similar question with new numbers
          </h2>
        </div>
        {toggle}
      </div>
      {open ? (
        <div className="mk-fade-in mt-4 rounded-card bg-mk-bg p-[18px]">
          <QuestionCard
            examId={examId}
            question={data}
            allAssets={assets}
            selectedLabel={null}
            onSelect={() => {}}
            disabled={false}
            readOnly
            hideAudio
            compact
            showOutcome={false}
            correctLabel=""
            metaLabel="Similar question"
            resolveAssetUrl={(asset) =>
              generatedAssetUrl(examId, questionId, asset.path)
            }
          />
        </div>
      ) : null}
    </section>
  );
}
