import { NextRequest } from "next/server";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type RouteContext = {
  params: Promise<{ path: string[] }>;
};

function readAdminTokenFromRootEnv(): string | undefined {
  // In local development Next.js is started from the frontend directory.
  // The repository-root .env is therefore one directory above process.cwd().
  const candidates = [
    path.resolve(process.cwd(), "..", ".env"),
    path.resolve(process.cwd(), ".env"),
  ];

  for (const envPath of candidates) {
    if (!existsSync(envPath)) continue;

    const contents = readFileSync(envPath, "utf8").replace(/^\uFEFF/, "");
    const line = contents
      .split(/\r?\n/)
      .filter((entry) => /^\s*ADMIN_API_TOKEN\s*=/.test(entry))
      .at(-1);

    if (!line) continue;

    let value = line.slice(line.indexOf("=") + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }

    if (value && !value.startsWith("#")) return value;
  }

  return undefined;
}

async function proxy(request: NextRequest, context: RouteContext): Promise<Response> {
  const { path: segments } = await context.params;
  const adminToken = process.env.ADMIN_API_TOKEN || readAdminTokenFromRootEnv();

  if (!adminToken) {
    return Response.json(
      {
        detail:
          "Server configuration error: ADMIN_API_TOKEN was not found in the Next.js server environment or repository-root .env file.",
      },
      { status: 503 },
    );
  }

  const backendOrigin =
    process.env.ATTENDVISION_API_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://127.0.0.1:8000";
  const backendPath =
    segments.join("/") === "health" ? "/health" : `/api/${segments.join("/")}`;
  const target = new URL(backendPath, backendOrigin);
  target.search = request.nextUrl.search;

  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  const accept = request.headers.get("accept");
  if (contentType) headers.set("content-type", contentType);
  if (accept) headers.set("accept", accept);
  headers.set("authorization", `Bearer ${adminToken}`);

  const init: RequestInit = {
    method: request.method,
    headers,
    cache: "no-store",
    redirect: "manual",
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.arrayBuffer();
  }

  let upstream: Response;
  try {
    upstream = await fetch(target, init);
  } catch {
    return Response.json(
      {
        detail:
          "Unable to reach the AttendVision API. Check that the backend is running and ATTENDVISION_API_URL is correct.",
      },
      { status: 502 },
    );
  }

  const responseHeaders = new Headers();
  for (const name of ["content-type", "content-disposition", "cache-control"]) {
    const value = upstream.headers.get(name);
    if (value) responseHeaders.set(name, value);
  }

  return new Response(request.method === "HEAD" ? null : upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  });
}

export { proxy as GET, proxy as POST, proxy as PATCH, proxy as DELETE };
