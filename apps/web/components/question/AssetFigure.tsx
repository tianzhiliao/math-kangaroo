"use client";

import { rawExamFileUrl } from "@/lib/asset-url";
import type { AssetRecord } from "@/lib/types";
import { useEffect, useRef, useState } from "react";

/**
 * Inline figure only (no lightbox). Shows an --mk-ink-4 placeholder until the
 * image has loaded.
 */
export function AssetFigure({
  examId,
  asset,
  alt,
  className = "",
  variant = "stem",
  srcOverride,
}: {
  examId: string;
  asset: AssetRecord;
  alt: string;
  className?: string;
  variant?: "stem" | "stem-wide" | "choice" | "choice-compact";
  srcOverride?: string;
}) {
  const src = srcOverride ?? rawExamFileUrl(examId, asset.path);
  const imgRef = useRef<HTMLImageElement>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    setLoaded(Boolean(imgRef.current?.complete));
  }, [src]);

  const sizeClasses =
    variant === "stem"
      ? "max-h-[116px] md:max-h-[220px]"
      : variant === "stem-wide"
        ? "max-h-[220px] md:max-h-[320px]"
        : variant === "choice"
        ? "h-[104px]"
        : "h-[64px]";

  return (
    <div
      className={`mk-transition flex max-w-full items-center justify-center rounded-[10px] ${
        loaded ? "bg-transparent" : "bg-mk-ink-4"
      } ${className}`}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        ref={imgRef}
        src={src}
        alt={alt}
        width={asset.width}
        height={asset.height}
        onLoad={() => setLoaded(true)}
        className={`w-auto max-w-full object-contain ${sizeClasses}`}
        loading="lazy"
        decoding="async"
      />
    </div>
  );
}
