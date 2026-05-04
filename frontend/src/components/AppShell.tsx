"use client";

import dynamic from "next/dynamic";
import { usePathname } from "next/navigation";

const Sidebar = dynamic(() => import("@/components/Sidebar").then((mod) => mod.Sidebar), {
  ssr: false,
  loading: () => <aside className="min-h-screen w-68 shrink-0 border-r border-emerald-400/10 bg-[#05080d]" />,
});

const publicRoutes = new Set(["/", "/login"]);

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isPublicRoute = publicRoutes.has(pathname);
  const isOwnerPlatformRoute = pathname === "/owner" || pathname.startsWith("/owner/");

  if (isPublicRoute || isOwnerPlatformRoute) {
    return <main className="min-h-screen bg-[#03070b]">{children}</main>;
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="min-h-screen flex-1 min-w-0 bg-[#03070b]">{children}</main>
    </div>
  );
}
