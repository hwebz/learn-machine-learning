import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ filename: string }> }
) {
  const { filename } = await params;
  if (!/^[0-9a-f]{32}\.(png|jpg|webp|gif)$/.test(filename)) {
    return new Response("Image not found", { status: 404 });
  }

  try {
    const response = await fetch(`http://127.0.0.1:8000/media/${filename}`, {
      headers: { "X-API-Key": process.env.BACKEND_API_KEY || "changeme" },
      redirect: "error",
      signal: AbortSignal.timeout(20000),
      cache: "no-store",
    });
    if (!response.ok) {
      return new Response("Could not load generated image", { status: response.status });
    }
    const contentType = response.headers.get("Content-Type")?.split(";")[0];
    if (!contentType || !["image/png", "image/jpeg", "image/webp", "image/gif"].includes(contentType)) {
      return new Response("Invalid image response", { status: 502 });
    }
    return new Response(response.body, {
      headers: {
        "Content-Type": contentType,
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, max-age=86400",
      },
    });
  } catch {
    return new Response("Could not connect to image storage", { status: 502 });
  }
}
