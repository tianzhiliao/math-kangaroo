import { proxyAudioGetRequest, proxyAudioRequest } from "@/lib/fastapi-proxy";

export async function POST(request: Request) {
  return proxyAudioRequest(request, "/tts");
}

export async function GET(request: Request) {
  return proxyAudioGetRequest(request, "/tts");
}
