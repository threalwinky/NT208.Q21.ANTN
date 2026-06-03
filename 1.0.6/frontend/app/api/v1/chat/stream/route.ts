import { type NextRequest } from "next/server";

function resolveInternalApiBase() {
  const configured = process.env.INTERNAL_API_BASE_URL?.trim();
  if (configured) {
    return configured.replace(/\/$/, "");
  }
  return "http://backend:8000/api/v1";
}

const INTERNAL_API_BASE = resolveInternalApiBase();

export async function POST(request: NextRequest) {
  const body = await request.text();
  const cookieHeader = request.headers.get("Cookie") ?? "";

  const upstream = await fetch(`${INTERNAL_API_BASE}/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(cookieHeader ? { Cookie: cookieHeader } : {}),
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
