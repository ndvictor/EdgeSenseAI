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
    <div className="min-h-screen bg-slate-500 p-4 lg:p-6">
      <div className="mx-auto w-full max-w-[1600px]">
        <PageHeader eyebrow={eyebrow} title={title} description={description} />
        <div className="rounded-xl border border-emerald-800 bg-slate-950 p-4 shadow-sm">
          <h2 className="mb-3 text-lg font-semibold text-emerald-500">Build scope</h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {bullets.map((bullet) => (
              <div key={bullet} className="rounded-lg border border-slate-800 bg-slate-900 px-4 py-3 text-sm leading-relaxed text-slate-300">
                {bullet}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
