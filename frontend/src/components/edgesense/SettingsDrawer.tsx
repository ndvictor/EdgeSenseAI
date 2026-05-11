"use client";

import { useEffect } from "react";

import {
  GateSettingsPanel,
  type TradingGatesResponse,
} from "@/components/edgesense/GateSettingsPanel";
import { WorkflowRunPanel } from "@/components/edgesense/WorkflowRunPanel";

export function SettingsDrawer({
  open,
  onClose,
  gates,
  onGatesChanged,
}: {
  open: boolean;
  onClose: () => void;
  gates: TradingGatesResponse | null;
  onGatesChanged: (response: TradingGatesResponse) => void;
}) {
  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  useEffect(() => {
    if (typeof document === "undefined") return;
    const previous = document.body.style.overflow;
    if (open) document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [open]);

  return (
    <div
      aria-hidden={!open}
      className={`fixed inset-0 z-50 ${open ? "pointer-events-auto" : "pointer-events-none"}`}
    >
      <button
        type="button"
        aria-label="Close settings"
        onClick={onClose}
        className={`absolute inset-0 cursor-default bg-black/60 backdrop-blur-sm transition-opacity ${
          open ? "opacity-100" : "opacity-0"
        }`}
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-label="Settings"
        className={`absolute right-0 top-0 flex h-full w-full max-w-[640px] flex-col border-l border-cyan-400/15 bg-[#02080d] shadow-[0_30px_120px_rgba(0,0,0,0.6)] transition-transform duration-200 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <header className="flex items-center justify-between border-b border-white/[0.06] px-5 py-4">
          <div>
            <div className="text-[10px] font-bold uppercase tracking-[0.22em] text-cyan-300/70">EdgeSenseAI</div>
            <h2 className="mt-1 text-lg font-black text-white">Settings</h2>
            <p className="mt-0.5 text-[11px] leading-4 text-slate-500">
              Gate configuration and workflow run controls. The broker is never called while editing.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs font-bold text-slate-200 hover:bg-white/[0.08]"
          >
            Close
          </button>
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
          <GateSettingsPanel onGatesChanged={onGatesChanged} />
          <WorkflowRunPanel gates={gates} />
        </div>
      </aside>
    </div>
  );
}
