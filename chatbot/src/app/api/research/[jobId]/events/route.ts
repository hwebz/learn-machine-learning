import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ jobId: string }> }
) {
  const { jobId } = await params;
  const backendUrl = `http://127.0.0.1:8000/research/${jobId}/events`;

  try {
    const backendRes = await fetch(backendUrl, {
      method: "GET",
      headers: {
        "X-API-Key": "changeme",
        Accept: "text/event-stream",
      },
      cache: "no-store",
    });

    if (!backendRes.ok) {
      return new Response(`Backend SSE error: ${backendRes.status}`, {
        status: backendRes.status,
      });
    }

    // Forward the SSE stream directly to the client browser
    return new Response(backendRes.body, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
        "X-Accel-Buffering": "no",
      },
    });
  } catch (error: any) {
    return new Response(`Failed to connect to backend SSE stream: ${error?.message}`, {
      status: 502,
    });
  }
}
