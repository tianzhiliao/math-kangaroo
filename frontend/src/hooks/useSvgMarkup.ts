/* eslint-disable react-hooks/set-state-in-effect */
import { useEffect, useState } from 'react';

const svgMarkupCache = new Map<string, string | null>();
const svgMarkupRequests = new Map<string, Promise<string | null>>();

async function loadSvgMarkup(svgPath: string): Promise<string | null> {
  if (svgMarkupCache.has(svgPath)) {
    return svgMarkupCache.get(svgPath) ?? null;
  }

  const inFlight = svgMarkupRequests.get(svgPath);
  if (inFlight) {
    return inFlight;
  }

  const request = fetch(svgPath)
    .then(async (response) => {
      if (!response.ok) {
        return null;
      }

      return response.text();
    })
    .catch(() => null)
    .then((markup) => {
      svgMarkupCache.set(svgPath, markup);
      svgMarkupRequests.delete(svgPath);
      return markup;
    });

  svgMarkupRequests.set(svgPath, request);
  return request;
}

export function useSvgMarkup(svgPath?: string) {
  const [markup, setMarkup] = useState<string | null>(() => {
    if (!svgPath || !svgMarkupCache.has(svgPath)) {
      return null;
    }

    return svgMarkupCache.get(svgPath) ?? null;
  });
  const [isLoading, setIsLoading] = useState(
    () => (svgPath ? !svgMarkupCache.has(svgPath) : false),
  );

  useEffect(() => {
    let cancelled = false;

    if (!svgPath) {
      setMarkup(null);
      setIsLoading(false);
      return () => {
        cancelled = true;
      };
    }

    if (svgMarkupCache.has(svgPath)) {
      setMarkup(svgMarkupCache.get(svgPath) ?? null);
      setIsLoading(false);
      return () => {
        cancelled = true;
      };
    }

    setMarkup(null);
    setIsLoading(true);

    void loadSvgMarkup(svgPath).then((nextMarkup) => {
      if (cancelled) {
        return;
      }

      setMarkup(nextMarkup);
      setIsLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, [svgPath]);

  return { markup, isLoading };
}
