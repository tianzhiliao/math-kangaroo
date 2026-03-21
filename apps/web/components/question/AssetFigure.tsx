import { rawExamFileUrl } from "@/lib/asset-url";
import type { AssetRecord } from "@/lib/types";

/**
 * Inline figure only (no lightbox). Sized for one-screen question layouts.
 */
export function AssetFigure({
  examId,
  asset,
  alt,
  className = "",
  variant = "stem",
}: {
  examId: string;
  asset: AssetRecord;
  alt: string;
  className?: string;
  variant?: "stem" | "choice";
}) {
  const src = rawExamFileUrl(examId, asset.path);
  const shortSide = Math.min(asset.width, asset.height);

  const stemClasses =
    "max-h-[min(26vh,200px)] w-auto max-w-[min(100%,min(92vw,480px))]";

  const choiceClasses =
    shortSide < 80
      ? "max-h-[min(14vh,100px)] w-auto max-w-[min(100%,110px)]"
      : "max-h-[min(20vh,150px)] w-auto max-w-[min(100%,min(42vw,180px))]";

  return (
    <div className={`mx-auto flex max-w-full justify-center ${className}`}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt={alt}
        width={asset.width}
        height={asset.height}
        className={`h-auto object-contain ${variant === "stem" ? stemClasses : choiceClasses}`}
        loading="lazy"
        decoding="async"
      />
    </div>
  );
}
