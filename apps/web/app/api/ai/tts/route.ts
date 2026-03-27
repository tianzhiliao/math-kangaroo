import {
  aiFeatureDisabledResponse,
  isAiEnabledOnServer,
} from "@/lib/ai-features";
import { proxyAudioGetRequest, proxyAudioRequest } from "@/lib/fastapi-proxy";

export async function POST(request: Request) {
  if (!isAiEnabledOnServer()) {
    return aiFeatureDisabledResponse();
  }
  return proxyAudioRequest(request, "/tts");
}

export async function GET(request: Request) {
  if (!isAiEnabledOnServer()) {
    return aiFeatureDisabledResponse();
  }
  return proxyAudioGetRequest(request, "/tts");
}
