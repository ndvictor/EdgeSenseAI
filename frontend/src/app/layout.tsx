import type { Metadata } from "next";
import "./globals.css";
import { AppShell } from "@/components/AppShell";

export const metadata: Metadata = {
  title: "EdgeSenseAI",
  description: "Personal trading intelligence operating system for account growth, risk control, and high-quality trade selection.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-[#03070b] text-slate-100">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
