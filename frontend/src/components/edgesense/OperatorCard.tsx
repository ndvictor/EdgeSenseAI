export function OperatorCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-3xl border border-white/10 bg-white/[0.035] p-5">
      <h2 className="mb-4 text-sm font-black uppercase tracking-[0.16em] text-cyan-50">{title}</h2>
      {children}
    </section>
  );
}
