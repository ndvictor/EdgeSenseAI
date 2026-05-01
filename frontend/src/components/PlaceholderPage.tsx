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
    <div className="p-6">
      <PageHeader eyebrow={eyebrow} title={title} description={description} />
      <div className="rounded-2xl border border-white/10 bg-white p-6">
        <h2 className="text-xl font-black text-white">Build scope</h2>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
          {bullets.map((bullet) => (
            <div key={bullet} className="rounded-xl border border-white/10 bg-white p-4 text-sm text-slate-300">
              {bullet}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
