import { proxyJsonRequest } from "@/lib/fastapi-proxy";

export async function POST(request: Request) {
  return proxyJsonRequest(request, "/ai/explanation");
}
