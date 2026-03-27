export interface ApiErrorPayload {
  error?: string;
  message?: string;
  detail?: string;
  upstream_status?: number;
}

export class ApiRequestError extends Error {
  code: string;
  status: number;
  detail?: string;

  constructor({
    code,
    message,
    status,
    detail,
  }: {
    code: string;
    message: string;
    status: number;
    detail?: string;
  }) {
    super(message);
    this.name = "ApiRequestError";
    this.code = code;
    this.status = status;
    this.detail = detail;
  }
}

export async function readApiError(
  response: Response,
  fallbackMessage: string,
): Promise<ApiRequestError> {
  const contentType = response.headers.get("content-type") ?? "";
  let code = "request_failed";
  let message = fallbackMessage;
  let detail: string | undefined;

  if (contentType.includes("application/json")) {
    try {
      const payload = (await response.json()) as ApiErrorPayload;
      if (typeof payload.error === "string" && payload.error.trim()) {
        code = payload.error;
      }
      if (typeof payload.detail === "string" && payload.detail.trim()) {
        detail = payload.detail;
      }
      if (typeof payload.message === "string" && payload.message.trim()) {
        message = payload.message;
      } else if (detail) {
        message = detail;
      }
    } catch {
      // Fall back to the generic message below.
    }
  } else {
    const text = (await response.text()).trim();
    if (text) {
      message = text;
    }
  }

  return new ApiRequestError({
    code,
    message,
    status: response.status,
    detail,
  });
}

export function getFriendlyAiErrorMessage(
  error: unknown,
  fallbackMessage: string,
): string {
  if (error instanceof ApiRequestError) {
    if (error.code === "backend_unreachable") {
      return "AI backend is not running. Start local dev with ./scripts/dev.sh.";
    }
    if (error.code === "malformed_upstream_response") {
      return "The AI backend returned an invalid response. Please try again.";
    }
    if (error.detail === "no_stem_text") {
      return "This question does not have text to read aloud.";
    }
    return error.message;
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  return fallbackMessage;
}
