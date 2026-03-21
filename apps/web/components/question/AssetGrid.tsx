import type { AssetRecord } from "@/lib/types";
import { AssetFigure } from "./AssetFigure";

export function AssetGrid({
  examId,
  assets,
  altPrefix,
}: {
  examId: string;
  assets: AssetRecord[];
  altPrefix: string;
}) {
  if (assets.length === 0) return null;
  if (assets.length === 1) {
    return (
      <AssetFigure
        examId={examId}
        asset={assets[0]}
        alt={`${altPrefix} figure`}
        variant="stem"
      />
    );
  }
  return (
    <div className="grid w-full grid-cols-2 gap-2 sm:gap-3">
      {assets.map((a, i) => (
        <AssetFigure
          key={a.id}
          examId={examId}
          asset={a}
          alt={`${altPrefix} figure ${i + 1}`}
          variant="stem"
        />
      ))}
    </div>
  );
}
