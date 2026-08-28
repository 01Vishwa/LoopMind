import { NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";

const PUBLIC_ROUTES = [
  "/login", "/signup",
  "/auth/callback", "/auth/reset-password", "/auth/forgot-password",
];

export async function middleware(request: any) {
  let response = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => request.cookies.getAll(),
        setAll: (cookiesToSet) => {
          // IMPORTANT ORDERING: write refreshed cookies onto BOTH the
          // incoming request (so downstream RSC reads see the new token in
          // this same pass) and onto a fresh response object — writing only
          // to `response` after it was already returned is the race condition
          // that intermittently bounced valid sessions to /login.
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
          response = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  // getUser(), not getSession(): getSession() only reads the local cookie
  // and can return a stale/forged-looking session without contacting
  // Supabase; getUser() revalidates against the auth server.
  const { data: { user } } = await supabase.auth.getUser();

  const path = request.nextUrl.pathname;
  
  if (
    path.startsWith("/_next") ||
    path.startsWith("/api") ||
    path.startsWith("/favicon") ||
    path.includes(".")
  ) {
    return response;
  }

  const isPublic = PUBLIC_ROUTES.some((r) => path.startsWith(r) || path === r);

  if (!user && !isPublic) {
    const redirectUrl = new URL("/login", request.url);
    redirectUrl.searchParams.set("next", path); // preserve intended destination
    return NextResponse.redirect(redirectUrl);
  }

  if (user && (path === "/login" || path === "/signup")) {
    return NextResponse.redirect(new URL("/workspaces", request.url));
  }

  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
