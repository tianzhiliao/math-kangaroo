import type { ReactNode } from 'react';
import type { Graphic } from '../../types/exam';
import { useSvgMarkup } from '../../hooks/useSvgMarkup';

interface SvgGraphicProps {
  graphic: Graphic;
  className: string;
  fallback: ReactNode;
  loadingFallback?: ReactNode;
}

export function SvgGraphic({
  graphic,
  className,
  fallback,
  loadingFallback,
}: SvgGraphicProps) {
  const { markup, isLoading } = useSvgMarkup(graphic.svg_path);

  if (markup) {
    return (
      <div
        className={className}
        dangerouslySetInnerHTML={{ __html: markup }}
      />
    );
  }

  if (isLoading && loadingFallback) {
    return <>{loadingFallback}</>;
  }

  return <>{fallback}</>;
}
