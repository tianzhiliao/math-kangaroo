import {
  aiFeatureDisabledResponse,
  isAiEnabledOnServer,
} from "@/lib/ai-features";
import { proxyJsonRequest } from "@/lib/fastapi-proxy";

export async function POST(request: Request) {
  if (!isAiEnabledOnServer()) {
    return aiFeatureDisabledResponse();
  }
  return proxyJsonRequest(request, "/ai/explanation");
}
