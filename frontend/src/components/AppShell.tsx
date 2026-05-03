"use client";

import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/Sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isHome = pathname === "/";

  if (isHome) {
    return <main className="flex flex-col min-h-screen bg-white flex items-center justify-center">{children}</main>;
  }

  // Changed to white / very light green-white
  return (
    <div className="flex flex-col min-h-screen bg-white flex items-center justify-center">
      <Sidebar />
      <main className="min-w-0 flex-1 p-8">{children}</main>
    </div>
  );
}