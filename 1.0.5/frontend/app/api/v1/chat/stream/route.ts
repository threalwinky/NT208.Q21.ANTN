import { type NextRequest } from "next/server";
import { readFileSync } from "fs";

function readDockerGateway() {
  try {
    const route = readFileSync("/proc/net/route", "utf8");
    const defaultRoute = route.split("\n").find((line) => line.includes("\t00000000\t"));
    const gatewayHex = defaultRoute?.split("\t")[2];
    if (!gatewayHex) return null;
    return [3, 2, 1, 0].map((index) => parseInt(gatewayHex.slice(index * 2, index * 2 + 2), 16)).join(".");
  } catch {
    return null;
  }
}

function resolveInternalApiBase() {
  const configured = process.env.INTERNAL_API_BASE_URL?.trim();
  if (configured) {
    return configured.replace(/\/$/, "");
  }

  const dockerGateway = readDockerGateway();
  const fallbackApiBase = dockerGateway ? `http://${dockerGateway}:8000/api/v1` : "http://localhost:8000/api/v1";
  return fallbackApiBase.replace(/\/$/, "");
}

const INTERNAL_API_BASE = resolveInternalApiBase();

export async function POST(request: NextRequest) {
  const body = await request.text();
  const authHeader = request.headers.get("Authorization") ?? "";

  const upstream = await fetch(`${INTERNAL_API_BASE}/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(authHeader ? { Authorization: authHeader } : {}),
    },
    body,
  });

  if (!upstream.ok || !upstream.body) {
    const errorText = await upstream.text().catch(() => "Đã có lỗi xảy ra.");
    return new Response(errorText, {
      status: upstream.status,
      headers: { "Content-Type": "application/json" },
    });
  }

  // Pipe the SSE stream directly without any buffering.
  return new Response(upstream.body, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
