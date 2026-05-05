"use client";

/**
 * Owner-style backdrop for the main engineering sidebar portal (all routes except /, /login, /owner/*, /ops/*).
 * Renders gradient wash + grid; parent should be `relative min-h-screen bg-emerald-950 overflow-hidden`.
 */
export function PlatformPortalScaffold({ children }: { children: React.ReactNode }) {
  return (
    <>
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_62%_0%,rgba(16,185,129,0.16),transparent_28%),radial-gradient(circle_at_0%_100%,rgba(20,184,166,0.08),transparent_28%)]"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute right-0 top-0 h-72 w-[55rem] rounded-full border-t border-emerald-300/30 blur-[0.2px]"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute inset-0 opacity-25 [background-image:linear-gradient(rgba(16,185,129,0.06)_1px,transparent_1px),linear-gradient(90deg,rgba(16,185,129,0.06)_1px,transparent_1px)] [background-size:54px_54px]"
        aria-hidden
      />
      <div className="relative z-10 min-h-full min-w-0 text-white">{children}</div>
    </>
  );
}
