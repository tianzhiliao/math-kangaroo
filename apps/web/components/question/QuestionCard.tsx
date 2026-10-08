"use client";

import { getFriendlyAiErrorMessage, readApiError } from "@/lib/api-errors";
import type { AssetRecord, Question } from "@/lib/types";
import { useEffect, useRef, useState } from "react";
import { AssetFigure } from "./AssetFigure";
import { AssetGrid } from "./AssetGrid";
import { SpeakerIcon, Spinner } from "@/components/ui/icons";

function buildAssetMap(assets: AssetRecord[]): Record<string, AssetRecord> {
  return Object.fromEntries(assets.map((a) => [a.id, a]));
}

type TtsStatus = "idle" | "loading" | "playing" | "error";

function StemTtsButton({
  examId,
  questionNumber,
}: {
  examId: string;
  questionNumber: number;
}) {
  const [status, setStatus] = useState<TtsStatus>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const objectUrlRef = useRef<string | null>(null);

  const releaseObjectUrl = () => {
    if (objectUrlRef.current) {
      URL.revokeObjectURL(objectUrlRef.current);
      objectUrlRef.current = null;
    }
  };

  const disposeAudio = () => {
    const audio = audioRef.current;
    if (audio) {
      audio.pause();
      audio.currentTime = 0;
      audioRef.current = null;
    }
    releaseObjectUrl();
  };

  useEffect(() => {
    return () => {
      disposeAudio();
    };
    // The button is tied to a single question; clean up on unmount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    disposeAudio();
    setStatus("idle");
    setErrorMessage(null);
    // Reset the TTS state whenever we navigate to a different question.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [examId, questionNumber]);

  const handleClick = async () => {
    if (status === "loading") return;
    if (status === "playing") {
      disposeAudio();
      setStatus("idle");
      return;
    }

    disposeAudio();
    setStatus("loading");
    setErrorMessage(null);

    try {
      const query = new URLSearchParams({
        exam_id: examId,
        question_number: String(questionNumber),
        format: "opus",
      });
      const response = await fetch(`/api/ai/tts?${query.toString()}`);
      if (!response.ok) {
        throw await readApiError(response, "Could not load the audio.");
      }
      const contentType = response.headers.get("content-type") ?? "";
      if (!contentType.startsWith("audio/")) {
        throw new Error("AI backend returned an invalid audio response.");
      }
      const audioBlob = await response.blob();
      if (!audioBlob.size) {
        throw new Error("AI backend returned an empty audio response.");
      }
      const objectUrl = URL.createObjectURL(audioBlob);
      objectUrlRef.current = objectUrl;

      const audio = new Audio(objectUrl);
      audio.preload = "auto";
      audioRef.current = audio;
      audio.onended = () => {
        disposeAudio();
        setStatus("idle");
      };
      audio.onerror = () => {
        disposeAudio();
        setStatus("error");
        setErrorMessage("Could not play the audio.");
      };

      await audio.play();
      setStatus("playing");
    } catch (error) {
      disposeAudio();
      setStatus("error");
      setErrorMessage(
        getFriendlyAiErrorMessage(error, "Could not play the audio."),
      );
    }
  };

  const label =
    status === "playing"
      ? "Stop audio"
      : status === "loading"
        ? "Loading audio"
        : "Listen to question";

  const tone =
    status === "playing"
      ? "bg-mk-ink-100 text-mk-inverse hover:bg-mk-ink-80"
      : status === "loading"
        ? "cursor-wait bg-mk-ink-4 text-mk-ink-60"
        : status === "error"
          ? "bg-mk-wrong-soft text-mk-wrong-fg hover:bg-mk-wrong-dot"
          : "bg-mk-raised text-mk-ink-100 hover:bg-mk-solid-12";

  return (
    <div className="flex shrink-0 flex-col items-end gap-1">
      <button
        type="button"
        onClick={handleClick}
        disabled={status === "loading"}
        aria-label={label}
        title={label}
        aria-busy={status === "loading"}
        className={`mk-transition inline-flex h-11 w-11 items-center justify-center rounded-full ${tone}`}
      >
        {status === "loading" ? (
          <Spinner />
        ) : status === "playing" ? (
          <span aria-hidden className="h-3 w-3 rounded-[3px] bg-current" />
        ) : (
          <SpeakerIcon />
        )}
      </button>
      {errorMessage ? (
        <p className="max-w-[160px] text-right text-caption text-mk-wrong-fg">
          {errorMessage}
        </p>
      ) : null}
    </div>
  );
}

type ChoiceState = "default" | "selected" | "right" | "wrong" | "dim";

const CARD_TONE: Record<ChoiceState, string> = {
  default: "border-mk-ink-12 bg-mk-bg",
  selected: "border-mk-ink-100 bg-mk-bg",
  right: "border-mk-right-strong bg-mk-right-surface",
  wrong: "border-mk-wrong-strong bg-mk-wrong-surface",
  dim: "border-mk-ink-12 bg-mk-bg opacity-50",
};

const BADGE_TONE: Record<ChoiceState, string> = {
  default: "bg-mk-raised text-mk-ink-100",
  selected: "bg-mk-ink-100 text-mk-inverse",
  right: "bg-mk-right-strong text-mk-inverse",
  wrong: "bg-mk-wrong-fg text-mk-inverse",
  dim: "bg-mk-raised text-mk-ink-100",
};

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
  /** Replaces the default "Question n · p points" meta line. */
  metaLabel,
  /** Points for the meta line when the question record has none. */
  points,
  /** Rendered under the stem, e.g. the result pill after submitting. */
  outcomeNote,
  readOnly = false,
  hideAudio = false,
  /** Dense layout for the read-only similar question. */
  compact = false,
  resolveAssetUrl,
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
  metaLabel?: string;
  points?: number;
  outcomeNote?: React.ReactNode;
  readOnly?: boolean;
  hideAudio?: boolean;
  compact?: boolean;
  resolveAssetUrl?: (asset: AssetRecord) => string;
}) {
  const map = buildAssetMap(allAssets);
  const stemAssets = question.shared_asset_refs
    .map((id) => map[id])
    .filter(Boolean);

  const hasStemFigure = stemAssets.length > 0;
  const hasStemText = question.stem_text.trim().length > 0;
  const imageChoices = question.choices.some((c) => c.asset_refs.length > 0);
  const questionPoints = question.points ?? points;
  const meta =
    metaLabel ??
    `Question ${displayQuestionNumber ?? question.number}${
      questionPoints ? ` · ${questionPoints} points` : ""
    }`;

  const gridCols = compact
    ? "grid-cols-[repeat(auto-fill,minmax(120px,1fr))]"
    : imageChoices
      ? "grid-cols-1 md:grid-cols-[repeat(auto-fill,minmax(150px,1fr))]"
      : "grid-cols-1 md:grid-cols-[repeat(auto-fill,minmax(250px,1fr))]";

  return (
    <article className="w-full">
      <div className="flex flex-wrap items-start gap-x-7 gap-y-4">
        <div className="min-w-0 flex-[1_1_360px]">
          <div className="flex min-h-[44px] items-center justify-between gap-3">
            <p className="text-meta-m text-mk-ink-60 md:text-meta">{meta}</p>
            {hasStemText && !hideAudio ? (
              <StemTtsButton
                examId={examId}
                questionNumber={question.number}
              />
            ) : null}
          </div>
          {hasStemText ? (
            <p
              className={`mt-3 text-pretty ${compact ? "text-h5" : "text-stem-m md:text-stem"}`}
            >
              {question.stem_text}
            </p>
          ) : null}
          {outcomeNote ? <div className="mt-4">{outcomeNote}</div> : null}
        </div>
        {hasStemFigure ? (
          <div
            className={`flex w-full justify-center rounded-card border border-mk-ink-12 bg-mk-bg p-3 ${
              compact
                ? "basis-full"
                : "md:w-auto md:min-w-[180px] md:max-w-[min(45%,360px)]"
            }`}
          >
            <AssetGrid
              examId={examId}
              assets={stemAssets}
              altPrefix={`Question ${question.number}`}
              srcFor={resolveAssetUrl}
              variant={compact ? "stem-wide" : "stem"}
            />
          </div>
        ) : null}
      </div>

      <div
        className={`grid ${gridCols} ${compact ? "mt-4 gap-2" : "mt-7 gap-2 md:gap-3"}`}
        role="list"
      >
        {question.choices.map((choice) => {
          const isSelected = selectedLabel === choice.label;
          const isCorrect = choice.label === correctLabel;
          const interactive = !disabled && !readOnly;

          let state: ChoiceState = "default";
          let tag: { text: string; className: string } | null = null;
          if (showOutcome) {
            if (isCorrect) {
              state = "right";
              tag = {
                text: isSelected ? "Your answer" : "Right answer",
                className: "text-mk-right-strong",
              };
            } else if (isSelected) {
              state = "wrong";
              tag = { text: "Your answer", className: "text-mk-wrong-fg" };
            } else {
              state = "dim";
            }
          } else if (isSelected) {
            state = "selected";
          } else if (disabled && !readOnly) {
            state = "dim";
          }

          const assetList = choice.asset_refs
            .map((id) => map[id])
            .filter(Boolean);
          const multiImg = assetList.length > 1;
          const hasText = choice.text.trim().length > 0;

          const badge = (
            <span
              className={`mk-transition flex shrink-0 items-center justify-center rounded-full ${BADGE_TONE[state]} ${
                compact
                  ? "h-8 w-8 text-[16px] font-medium leading-5"
                  : imageChoices
                    ? "h-10 w-10 text-choice-m md:text-choice"
                    : "h-11 w-11 text-choice-m md:text-choice"
              }`}
            >
              {choice.label}
            </span>
          );
          const tagEl = tag ? (
            <span className={`ml-auto shrink-0 text-caption ${tag.className}`}>
              {tag.text}
            </span>
          ) : null;

          const body = imageChoices ? (
            <>
              <span className="flex min-h-[40px] items-center gap-3">
                {badge}
                {hasText ? (
                  <span className="min-w-0 text-h5">{choice.text}</span>
                ) : null}
                {tagEl}
              </span>
              {assetList.length > 0 ? (
                <span
                  className={
                    multiImg
                      ? "flex flex-row flex-wrap justify-center gap-1.5"
                      : "flex justify-center"
                  }
                >
                  {assetList.map((a, i) => (
                    <AssetFigure
                      key={`${choice.label}-${a.id}-${i}`}
                      examId={examId}
                      asset={a}
                      alt={`Option ${choice.label} figure ${i + 1}`}
                      variant={compact ? "choice-compact" : "choice"}
                      className={multiImg ? "max-w-[calc(50%-0.25rem)]" : ""}
                      srcOverride={resolveAssetUrl?.(a)}
                    />
                  ))}
                </span>
              ) : null}
            </>
          ) : (
            <>
              {badge}
              {hasText ? (
                <span
                  className={`min-w-0 flex-1 ${compact ? "text-[16px] font-medium leading-6" : "text-choice-m md:text-choice"}`}
                >
                  {choice.text}
                </span>
              ) : null}
              {tagEl}
            </>
          );

          const cardClass = `mk-transition flex w-full rounded-card border-2 text-left ${CARD_TONE[state]} ${
            imageChoices
              ? `flex-col items-stretch gap-2 ${compact ? "p-2" : "p-3"}`
              : `items-center gap-3 ${compact ? "min-h-[48px] py-2 pl-2 pr-3" : "min-h-[54px] py-[10px] pl-3 pr-[18px] md:min-h-[64px]"}`
          } ${interactive && state === "default" ? "hover:border-mk-ink-44 hover:bg-mk-ink-2" : ""}`;

          return (
            <div key={choice.label} role="listitem" className="flex">
              {readOnly ? (
                <div className={cardClass}>{body}</div>
              ) : (
                <button
                  type="button"
                  aria-pressed={isSelected}
                  aria-label={`Option ${choice.label}${hasText ? `: ${choice.text}` : ""}${tag ? ` (${tag.text})` : ""}`}
                  disabled={disabled}
                  onClick={() => onSelect(choice.label)}
                  className={`${cardClass} ${disabled ? "cursor-default" : "cursor-pointer"}`}
                >
                  {body}
                </button>
              )}
            </div>
          );
        })}
      </div>
    </article>
  );
}
