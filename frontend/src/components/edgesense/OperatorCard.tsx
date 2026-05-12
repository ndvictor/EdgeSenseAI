import type { JsonValue } from "@/lib/edgesense/types";
import { display } from "@/lib/edgesense/format";

export function OperatorCard({ title, description, children }: { title: string; description?: string; children: React.ReactNode }) {
  return (
    <section className="rounded-3xl border border-white/10 bg-white/[0.035] p-5 shadow-[0_20px_80px_rgba(0,0,0,0.35)] backdrop-blur">
      <div className="mb-4">
        <h2 className="text-sm font-black uppercase tracking-[0.16em] text-cyan-50">{title}</h2>
        {description ? <p className="mt-1 text-xs leading-5 text-slate-500">{description}</p> : null}
      </div>
      {children}
    </section>
  );
}

export function StatusBadge({ children, tone = "slate" }: { children: React.ReactNode; tone?: "cyan" | "emerald" | "amber" | "rose" | "slate" }) {
  const tones = {
    cyan: "border-cyan-300/30 bg-cyan-400/10 text-cyan-100",
    emerald: "border-emerald-300/30 bg-emerald-400/10 text-emerald-100",
    amber: "border-amber-300/30 bg-amber-400/10 text-amber-100",
    rose: "border-rose-300/30 bg-rose-400/10 text-rose-100",
    slate: "border-slate-500/30 bg-slate-500/10 text-slate-300",
  } as const;
  return <span className={`rounded-full border px-3 py-1 text-[11px] font-bold uppercase tracking-[0.14em] ${tones[tone]}`}>{children}</span>;
}

export function EmptyState({ text }: { text: string }) {
  return <div className="rounded-2xl border border-white/10 bg-black/20 p-5 text-sm text-slate-400">{text}</div>;
}

export function JsonViewer({ value }: { value: JsonValue | JsonValue[] | undefined | null }) {
  if (value === undefined || value === null || (Array.isArray(value) && value.length === 0)) return <EmptyState text="Unavailable" />;
  return <pre className="max-h-[360px] overflow-auto rounded-2xl border border-white/10 bg-black/30 p-4 text-xs leading-5 text-slate-300">{display(value)}</pre>;
}

export function KeyValueGrid({ rows }: { rows: { label: string; value: JsonValue | undefined | null }[] }) {
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {rows.map((row) => (
        <div key={row.label} className="rounded-2xl border border-white/10 bg-black/20 p-3">
          <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500">{row.label}</div>
          <div className="mt-1 break-words font-mono text-xs text-slate-200">{display(row.value)}</div>
        </div>
      ))}
    </div>
  );
}
