import path from "path";

/**
 * Resolve `release-data` directory. Override with RELEASE_DATA_PATH in Docker/production.
 */
export function getReleaseDataRoot(): string {
  if (process.env.RELEASE_DATA_PATH) {
    return path.resolve(process.env.RELEASE_DATA_PATH);
  }
  // apps/web -> repo root/release-data
  return path.resolve(process.cwd(), "..", "..", "release-data");
}
