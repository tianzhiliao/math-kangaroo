/**
 * Display names, cover colours and filter keys per paper series
 * (manifest/exam `level`). See docs/design/plan-c.md §7.2.
 */
export type SeriesInfo = {
  key: string;
  name: string;
  /** Tailwind background class for the paper cover. */
  coverClassName: string;
};

export const SERIES: SeriesInfo[] = [
  { key: "felix", name: "Felix · Austria", coverClassName: "bg-mk-series-felix" },
  {
    key: "level-p",
    name: "Level P · Brazil",
    coverClassName: "bg-mk-series-level-p",
  },
  {
    key: "grade-1-2",
    name: "Grade 1–2 · Canada",
    coverClassName: "bg-mk-series-grade-1-2",
  },
];

const BY_KEY = new Map(SERIES.map((s) => [s.key, s]));

export function seriesFor(level: string, family: string): SeriesInfo {
  return (
    BY_KEY.get(level) ?? {
      key: level,
      name: family,
      coverClassName: "bg-mk-raised",
    }
  );
}
