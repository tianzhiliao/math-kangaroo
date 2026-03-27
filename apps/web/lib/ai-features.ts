const AI_DISABLED_PAYLOAD = {
  error: "feature_disabled",
  message: "AI features are disabled in this deployment.",
};

export function isAiEnabledOnClient(): boolean {
  return process.env.NEXT_PUBLIC_ENABLE_AI === "true";
}

export function isAiEnabledOnServer(): boolean {
  return process.env.ENABLE_AI === "true";
}

export function aiFeatureDisabledResponse(): Response {
  return Response.json(AI_DISABLED_PAYLOAD, { status: 404 });
}
