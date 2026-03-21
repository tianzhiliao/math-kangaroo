"use client";

import type { AssetRecord, Question } from "@/lib/types";
import { AssetFigure } from "./AssetFigure";
import { AssetGrid } from "./AssetGrid";

function buildAssetMap(assets: AssetRecord[]): Record<string, AssetRecord> {
  return Object.fromEntries(assets.map((a) => [a.id, a]));
}

export function QuestionCard({
  examId,
  question,
  allAssets,
  selectedLabel,
  onSelect,
  disabled,
  showOutcome,
  correctLabel,
  /** When set (e.g. practice bank), overrides the printed question index */
  displayQuestionNumber,
}: {
  examId: string;
  question: Question;
  allAssets: AssetRecord[];
  selectedLabel: string | null;
  onSelect: (label: string) => void;
  disabled: boolean;
  showOutcome: boolean;
  correctLabel: string;
  displayQuestionNumber?: number;
}) {
  const map = buildAssetMap(allAssets);
  const stemAssets = question.shared_asset_refs
    .map((id) => map[id])
    .filter(Boolean);

  const hasStemFigure = stemAssets.length > 0;

  return (
    <article className="mx-auto flex w-full max-w-4xl flex-col rounded-2xl border-2 border-slate-200/90 bg-white px-3 py-3 shadow-sm sm:px-4 sm:py-4">
      {/* Stem: text + figure side-by-side on wide screens to save vertical space */}
      <div
        className={`flex min-w-0 flex-col gap-3 ${hasStemFigure ? "lg:flex-row lg:items-start lg:gap-4" : ""}`}
      >
        <div className="min-w-0 flex-1">
          <p className="text-center text-[11px] font-bold uppercase tracking-wider text-slate-500 lg:text-left">
            Question {displayQuestionNumber ?? question.number}
          </p>
          {question.stem_text.trim() ? (
            <p className="mt-1.5 text-balance text-center text-xl font-semibold leading-snug text-slate-900 sm:text-2xl lg:text-left">
              {question.stem_text}
            </p>
          ) : null}
        </div>
        {hasStemFigure ? (
          <div className="shrink-0 lg:max-w-[min(48%,320px)] lg:self-center">
            <AssetGrid
              examId={examId}
              assets={stemAssets}
              altPrefix={`Question ${question.number}`}
            />
          </div>
        ) : null}
      </div>

      {/* Options: dense grid; image options use compact inline figures */}
      <div
        className={`grid grid-cols-1 gap-2 sm:grid-cols-2 sm:gap-3 ${hasStemFigure || question.stem_text.trim() ? "mt-3 border-t border-slate-100 pt-3" : "mt-1"}`}
        role="list"
      >
        {question.choices.map((choice) => {
          const isSelected = selectedLabel === choice.label;
          const isCorrect = choice.label === correctLabel;
          let tone =
            "border-slate-200 bg-slate-50/80 hover:border-blue-300 hover:bg-blue-50/50";
          if (showOutcome) {
            if (isCorrect) {
              tone =
                "border-emerald-500 bg-emerald-50 ring-2 ring-emerald-400";
            } else if (isSelected && !isCorrect) {
              tone = "border-red-400 bg-red-50 ring-2 ring-red-300";
            } else {
              tone = "border-slate-100 bg-slate-50/60 opacity-90";
            }
          } else if (isSelected) {
            tone = "border-blue-500 bg-blue-50 ring-2 ring-blue-400";
          }

          const assetList = choice.asset_refs
            .map((id) => map[id])
            .filter(Boolean);
          const multiImg = assetList.length > 1;

          return (
            <div
              key={choice.label}
              role="button"
              tabIndex={disabled ? -1 : 0}
              aria-disabled={disabled}
              aria-pressed={isSelected}
              onKeyDown={(e) => {
                if (disabled) return;
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onSelect(choice.label);
                }
              }}
              onClick={() => {
                if (!disabled) onSelect(choice.label);
              }}
              className={`flex min-h-[44px] cursor-pointer flex-col gap-2 rounded-xl border-2 p-2.5 text-left transition sm:min-h-[48px] sm:p-3 ${tone} ${disabled ? "cursor-not-allowed opacity-60" : ""}`}
            >
              <div className="flex items-start gap-2 sm:gap-2.5">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-slate-800 text-base font-bold text-white sm:h-11 sm:w-11 sm:text-lg">
                  {choice.label}
                </span>
                {choice.text.trim() ? (
                  <span className="min-w-0 flex-1 text-base font-medium leading-snug text-slate-800 sm:text-lg">
                    {choice.text}
                  </span>
                ) : null}
              </div>
              {assetList.length > 0 ? (
                <div
                  className={
                    multiImg
                      ? "flex flex-row flex-wrap justify-center gap-1.5 sm:justify-start"
                      : "flex justify-center sm:justify-start"
                  }
                >
                  {assetList.map((a, i) => (
                    <AssetFigure
                      key={`${choice.label}-${a.id}-${i}`}
                      examId={examId}
                      asset={a}
                      alt={`Option ${choice.label} figure ${i + 1}`}
                      variant="choice"
                      className={multiImg ? "max-w-[calc(50%-0.25rem)]" : ""}
                    />
                  ))}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </article>
  );
}
