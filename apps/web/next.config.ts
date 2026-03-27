import path from "path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  outputFileTracingRoot: path.join(__dirname, "../../"),
  outputFileTracingIncludes: {
    "/api/exams": ["../../release-data/**/*"],
    "/api/exams/[examId]": ["../../release-data/**/*"],
    "/api/exams/[examId]/raw/[...path]": ["../../release-data/**/*"],
    "/api/practice-bank": ["../../release-data/**/*"],
  },
};

export default nextConfig;
