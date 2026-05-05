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
    <div className="w-full min-h-full p-4 lg:p-8">
      <div className="mx-auto w-full max-w-[1600px]">
        <PageHeader eyebrow={eyebrow} title={title} description={description} />
        <div className="rounded-2xl border border-emerald-400/15 bg-black/35 p-4 shadow-[0_0_40px_rgba(0,0,0,0.35)] backdrop-blur">
          <h2 className="mb-3 text-lg font-semibold text-emerald-300">Build scope</h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {bullets.map((bullet) => (
              <div key={bullet} className="rounded-lg border border-white/10 bg-white/[0.025] px-4 py-3 text-sm leading-relaxed text-slate-300">
                {bullet}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
