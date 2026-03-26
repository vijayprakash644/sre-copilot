import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";
const API_KEY = process.env.API_KEY ?? "";

/**
 * Catch-all proxy that forwards any request to the backend.
 * Path rewriting: /api/proxy/alerts → BACKEND_URL/alerts
 *
 * Supports GET, POST, PUT, PATCH, DELETE.
 */
async function proxyRequest(request: NextRequest): Promise<NextResponse> {
  // Strip /api/proxy prefix from the pathname
  const incomingPath = request.nextUrl.pathname.replace(/^\/api\/proxy/, "");
  const search = request.nextUrl.search ?? "";
  const targetUrl = `${BACKEND_URL}${incomingPath}${search}`;

  // Build forwarded headers
  const headers = new Headers();
  request.headers.forEach((value, key) => {
    // Skip headers that Next.js / the proxy should not forward
    if (
      key.toLowerCase() === "host" ||
      key.toLowerCase() === "connection" ||
      key.toLowerCase() === "transfer-encoding"
    ) {
      return;
    }
    headers.set(key, value);
  });

  if (API_KEY) {
    headers.set("X-API-Key", API_KEY);
  }

  // Read body (only for non-GET/HEAD methods)
  let body: BodyInit | null = null;
  if (!["GET", "HEAD"].includes(request.method.toUpperCase())) {
    body = await request.blob();
  }

  let backendRes: Response;
  try {
    backendRes = await fetch(targetUrl, {
      method: request.method,
      headers,
      body,
      // Pass through duplex for streaming bodies
      // @ts-expect-error — duplex is not in the standard fetch types yet
      duplex: "half",
    });
  } catch (err) {
    console.error("[proxy] fetch error:", err);
    return NextResponse.json(
      { error: "Backend unreachable", details: String(err) },
      { status: 502 }
    );
  }

  // Stream the response back
  const responseHeaders = new Headers();
  backendRes.headers.forEach((value, key) => {
    if (
      key.toLowerCase() !== "transfer-encoding" &&
      key.toLowerCase() !== "connection"
    ) {
      responseHeaders.set(key, value);
    }
  });

  return new NextResponse(backendRes.body, {
    status: backendRes.status,
    statusText: backendRes.statusText,
    headers: responseHeaders,
  });
}

export async function GET(request: NextRequest) {
  return proxyRequest(request);
}

export async function POST(request: NextRequest) {
  return proxyRequest(request);
}

export async function PUT(request: NextRequest) {
  return proxyRequest(request);
}

export async function PATCH(request: NextRequest) {
  return proxyRequest(request);
}

export async function DELETE(request: NextRequest) {
  return proxyRequest(request);
}
