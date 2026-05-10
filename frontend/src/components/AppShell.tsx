"use client";

import dynamic from "next/dynamic";
import { usePathname } from "next/navigation";

import { PlatformPortalScaffold } from "@/components/PlatformPortalScaffold";

const Sidebar = dynamic(() => import("@/components/Sidebar").then((mod) => mod.Sidebar), {
  ssr: false,
  loading: () => <aside className="min-h-screen w-68 shrink-0 border-r border-emerald-400/10 bg-[#05080d]" />,
});

const publicRoutes = new Set(["/", "/login"]);

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isPublicRoute = publicRoutes.has(pathname);
  const isOwnerPlatformRoute = pathname === "/owner" || pathname.startsWith("/owner/");
  const isOpsPlatformRoute = pathname === "/ops" || pathname.startsWith("/ops/");
  const isDayTradingPlatformRoute = pathname === "/daytrading-workflow" || pathname.startsWith("/daytrading-workflow/");
  const isDayTradingControlCenterRoute = pathname === "/daytrading-control-center" || pathname.startsWith("/daytrading-control-center/");

  if (isPublicRoute || isOwnerPlatformRoute || isOpsPlatformRoute || isDayTradingPlatformRoute || isDayTradingControlCenterRoute) {
    const publicBg = pathname === "/" || pathname === "/login" ? "bg-[#000000]" : "bg-[#03070b]";
    return <main className={`min-h-screen ${publicBg}`}>{children}</main>;
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="relative min-h-screen flex-1 min-w-0 overflow-hidden bg-emerald-950">
        <PlatformPortalScaffold>{children}</PlatformPortalScaffold>
      </main>
    </div>
  );
}
