import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-slate-950 text-slate-100">
        <div className="flex min-h-screen">   {/* This is key */}
          <Sidebar />
          
          {/* Main content area - also full height */}
          <main className="flex-1 min-w-0 bg-slate-500 min-h-screen">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}