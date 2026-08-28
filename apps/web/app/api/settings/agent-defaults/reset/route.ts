import { proxy } from "@/app/api/_lib/proxy";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const res = await proxy(request, { path: "/v1/settings/agent-defaults/reset" });
  return res ?? NextResponse.json({ error: "offline" }, { status: 502 });
}
