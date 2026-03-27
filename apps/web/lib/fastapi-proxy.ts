import { buildFastApiUrl } from "@/lib/fastapi";

const DEV_BACKEND_HINT =
  "AI backend is not running. Start local dev with ./scripts/dev.sh.";

interface ProxyErrorPayload {
  error: string;
  message: string;
  detail?: string;
  upstream_status?: number;
}

function jsonError(
  payload: ProxyErrorPayload,
  status: number,
): Response {
  return Response.json(payload, { status });
}

async function parseUpstreamError(response: Response): Promise<ProxyErrorPayload> {
  const contentType = response.headers.get("content-type") ?? "";
  let detail: string | undefined;
  let message = `AI backend request failed (${response.status}).`;

  if (contentType.includes("application/json")) {
    try {
      const payload = (await response.json()) as {
        error?: unknown;
        message?: unknown;
        detail?: unknown;
      };
      if (typeof payload.detail === "string" && payload.detail.trim()) {
        detail = payload.detail;
      }
      if (typeof payload.message === "string" && payload.message.trim()) {
        message = payload.message;
      } else if (detail) {
        message = detail;
      }
    } catch {
      return {
        error: "malformed_upstream_response",
        message: "AI backend returned an invalid error response.",
      };
    }
  } else {
    const text = (await response.text()).trim();
    if (text) {
      message = text;
    }
  }

  return {
    error: "upstream_error",
    message,
    detail,
    upstream_status: response.status,
  };
}

function cloneStreamingHeaders(headers: Headers): Headers {
  const copy = new Headers(headers);
  copy.delete("content-length");
  copy.delete("transfer-encoding");
  copy.delete("connection");
  return copy;
}

export async function proxyJsonRequest(
  request: Request,
  path: string,
): Promise<Response> {
  let upstream: Response;
  try {
    upstream = await fetch(buildFastApiUrl(path), {
      method: "POST",
      headers: {
        "content-type": request.headers.get("content-type") ?? "application/json",
      },
      body: await request.text(),
    });
  } catch {
    return jsonError(
      {
        error: "backend_unreachable",
        message: DEV_BACKEND_HINT,
      },
      502,
    );
  }

  if (!upstream.ok) {
    return jsonError(await parseUpstreamError(upstream), upstream.status);
  }

  const contentType = upstream.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return jsonError(
      {
        error: "malformed_upstream_response",
        message: "AI backend returned an invalid explanation response.",
      },
      502,
    );
  }

  const text = await upstream.text();
  if (!text.trim()) {
    return jsonError(
      {
        error: "malformed_upstream_response",
        message: "AI backend returned an empty explanation response.",
      },
      502,
    );
  }

  try {
    const parsed = JSON.parse(text);
    return Response.json(parsed, { status: upstream.status });
  } catch {
    return jsonError(
      {
        error: "malformed_upstream_response",
        message: "AI backend returned an invalid explanation response.",
      },
      502,
    );
  }
}

export async function proxyAudioRequest(
  request: Request,
  path: string,
): Promise<Response> {
  let upstream: Response;
  try {
    upstream = await fetch(buildFastApiUrl(path), {
      method: "POST",
      headers: {
        "content-type": request.headers.get("content-type") ?? "application/json",
      },
      body: await request.text(),
    });
  } catch {
    return jsonError(
      {
        error: "backend_unreachable",
        message: DEV_BACKEND_HINT,
      },
      502,
    );
  }

  if (!upstream.ok) {
    return jsonError(await parseUpstreamError(upstream), upstream.status);
  }

  const contentType = upstream.headers.get("content-type") ?? "";
  if (!contentType.startsWith("audio/") || !upstream.body) {
    return jsonError(
      {
        error: "malformed_upstream_response",
        message: "AI backend returned an invalid audio response.",
      },
      502,
    );
  }

  return new Response(upstream.body, {
    status: upstream.status,
    headers: cloneStreamingHeaders(upstream.headers),
  });
}

export async function proxyAudioGetRequest(
  request: Request,
  path: string,
): Promise<Response> {
  const incoming = new URL(request.url);
  const upstreamUrl = new URL(buildFastApiUrl(path));
  upstreamUrl.search = incoming.search;

  let upstream: Response;
  try {
    upstream = await fetch(upstreamUrl, {
      method: "GET",
    });
  } catch {
    return jsonError(
      {
        error: "backend_unreachable",
        message: DEV_BACKEND_HINT,
      },
      502,
    );
  }

  if (!upstream.ok) {
    return jsonError(await parseUpstreamError(upstream), upstream.status);
  }

  const contentType = upstream.headers.get("content-type") ?? "";
  if (!contentType.startsWith("audio/") || !upstream.body) {
    return jsonError(
      {
        error: "malformed_upstream_response",
        message: "AI backend returned an invalid audio response.",
      },
      502,
    );
  }

  return new Response(upstream.body, {
    status: upstream.status,
    headers: cloneStreamingHeaders(upstream.headers),
  });
}
