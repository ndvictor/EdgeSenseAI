"use client";

import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/Sidebar";

const publicRoutes = new Set(["/", "/login"]);

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isPublicRoute = publicRoutes.has(pathname);

  if (isPublicRoute) {
    return <main className="min-h-screen bg-[#03070b]">{children}</main>;
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="min-h-screen flex-1 min-w-0 bg-[#03070b]">{children}</main>
    </div>
  );
}
