export function getFastApiBaseUrl(): string {
  const raw = process.env.FASTAPI_BASE_URL?.trim();
  const base = raw && raw.length > 0 ? raw : "http://127.0.0.1:8000";
  return base.replace(/\/+$/, "");
}

export function buildFastApiUrl(path: string): string {
  const suffix = path.startsWith("/") ? path : `/${path}`;
  return `${getFastApiBaseUrl()}${suffix}`;
}
