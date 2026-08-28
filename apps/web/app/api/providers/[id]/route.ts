import { proxy } from "@/app/api/_lib/proxy";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function PATCH(request: Request, context: { params: { id: string } }) {
  const params = await context.params;
  const res = await proxy(request, { path: `/v1/providers/${params.id}` });
  return res ?? NextResponse.json({ error: "offline" }, { status: 502 });
}

export async function DELETE(request: Request, context: { params: { id: string } }) {
  const params = await context.params;
  const res = await proxy(request, { path: `/v1/providers/${params.id}` });
  return res ?? new NextResponse(null, { status: 204 });
}
