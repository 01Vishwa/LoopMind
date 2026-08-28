import { proxy } from "@/app/api/_lib/proxy";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const res = await proxy(request, { path: "/v1/settings/agent-defaults" });
  return res ?? NextResponse.json({ error: "offline" }, { status: 502 });
}

export async function PUT(request: Request) {
  const res = await proxy(request, { path: "/v1/settings/agent-defaults" });
  return res ?? NextResponse.json({ error: "offline" }, { status: 502 });
}
