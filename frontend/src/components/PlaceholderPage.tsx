import { PageHeader } from "@/components/Cards";

export function PlaceholderPage({
  eyebrow,
  title,
  description,
  bullets,
}: {
  eyebrow: string;
  title: string;
  description: string;
  bullets: string[];
}) {
  return (
    <div className="min-h-screen bg-slate-500 p-2 lg:p-3">
      <div className="mx-auto max-w-7xl">
        <PageHeader eyebrow={eyebrow} title={title} description={description} />
        <div className="rounded-xl border border-emerald-800 bg-slate-950 p-3 shadow-sm">
          <h2 className="mb-2 text-sm font-semibold text-emerald-500">Build scope</h2>
          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
            {bullets.map((bullet) => (
              <div key={bullet} className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-xs leading-snug text-slate-300">
                {bullet}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
