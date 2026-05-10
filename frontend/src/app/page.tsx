import Link from "next/link";

function accentBarClass(accent: string) {
  if (accent === "sky") return "bg-sky-400/90";
  if (accent === "violet") return "bg-violet-400/90";
  if (accent === "emerald") return "bg-emerald-400/90";
  if (accent === "amber") return "bg-amber-400/90";
  return "bg-cyan-400/90";
}

export default function Home() {
  const cards = [
    {
      title: "Production v1 Day-Trading Dashboard",
      subtitle: "Clean production workflow UI backed only by /api/v1/daytrading routes.",
      badges: ["v1 routes", "Production contract", "Paper-first", "No legacy fetches", "No broker submit"],
      cta: "Open v1 Dashboard",
      href: "/daytrading-workflow/new",
      accent: "emerald",
    },
    {
      title: "Day Trading Control Center",
      subtitle: "Mapped dashboard with route migration table, market-session visibility, and settings UI.",
      badges: ["Route map", "Settings", "Azure env", "Market session", "Migration view"],
      cta: "Open Control Center",
      href: "/daytrading-control-center",
      accent: "amber",
    },
    {
      title: "Classic Workflow View",
      subtitle: "Original visual surface kept for reference while legacy routes are migrated behind v1.",
      badges: ["Legacy visual", "Reference only", "May be blocked", "Do not wire new work here"],
      cta: "Open Classic View",
      href: "/daytrading-workflow",
      accent: "black",
    },
    {
      title: "Legacy Manual Trading",
      subtitle: "Manual research, TradeNow, candidates, command center, and legacy tools.",
      badges: ["Manual tools", "Research mode", "Not autonomous controller"],
      cta: "Open Manual Trading",
      href: "/manual-trading",
      accent: "sky",
    },
    {
      title: "Lab",
      subtitle: "Strategy tests, model tests, training, evidence review, and promotion workflow.",
      badges: ["Strategy research", "Model selection", "Qlib evidence", "Promotion gated"],
      cta: "Open Lab",
      href: "/lab",
      accent: "violet",
    },
  ];

  return (
    <main className="min-h-screen bg-[#000000] px-4 py-8 text-cyan-400 lg:px-10">
      <div className="mx-auto flex min-h-[calc(100vh-4rem)] w-full max-w-7xl flex-col justify-center">
        <div className="mb-10">
          <div className="mb-4 inline-flex rounded-full border border-white/10 bg-black/35 px-4 py-1.5 text-xs font-bold uppercase tracking-[0.22em] text-cyan-200 backdrop-blur-xl">
            EdgeSenseAI
          </div>
          <h1 className="max-w-3xl text-xl font-black tracking-[-0.04em] text-cyan-400 lg:text-5xl">
            Choose the right trading workspace.
          </h1>
          <p className="mt-4 max-w-4xl text-base leading-7 text-slate-400">
            The new production dashboard and control center are the source of truth for v1 route migration. The classic workflow remains available as a visual reference while legacy runtime routes are quarantined and migrated cleanly.
          </p>
        </div>

        <section className="grid gap-4 lg:grid-cols-3">
          {cards.map((card) => (
            <div
              key={card.href}
              className="relative rounded-3xl border border-cyan-900 bg-black/35 p-6 shadow-[0_0_40px_rgba(0,0,0,0.35)] backdrop-blur-4xl transition duration-200 ease-out hover:z-10 hover:scale-[1.02] hover:bg-cyan-700/30"
            >
              <div className={`mb-5 h-1.5 w-16 rounded-full ${accentBarClass(card.accent)}`} />
              <h2 className="text-2xl font-bold text-cyan-400/70">{card.title}</h2>
              <p className="mt-3 min-h-12 text-sm leading-6 text-slate-400">{card.subtitle}</p>
              <div className="mt-5 flex flex-wrap gap-2">
                {card.badges.map((badge) => (
                  <span
                    key={badge}
                    className="rounded-full border border-white/10 bg-white/[0.06] px-3 py-1 text-[10px] font-bold uppercase text-slate-400 backdrop-blur-sm"
                  >
                    {badge}
                  </span>
                ))}
              </div>
              <Link
                href={card.href}
                className="mt-8 inline-flex rounded-xl border border-cyan-400/30 bg-cyan-400/10 px-4 py-2.5 text-sm font-bold text-cyan-300 backdrop-blur-md transition hover:border-cyan-400/45 hover:bg-cyan-400/20"
              >
                {card.cta} →
              </Link>
            </div>
          ))}
        </section>

        <section className="mt-8 flex flex-wrap gap-3 text-sm">
          <Link
            href="/daytrading-control-center#settings"
            className="rounded-xl border border-amber-400/35 bg-black/35 px-4 py-2 text-amber-100 backdrop-blur-xl transition hover:bg-amber-400/10"
          >
            Settings UI →
          </Link>
          <Link
            href="/daytrading-control-center#mapping"
            className="rounded-xl border border-cyan-400/35 bg-black/35 px-4 py-2 text-cyan-100 backdrop-blur-xl transition hover:bg-cyan-400/10"
          >
            Route Mapping →
          </Link>
          <Link
            href="/owner"
            className="rounded-xl border border-white/10 bg-black/35 px-4 py-2 text-slate-300 backdrop-blur-xl transition hover:bg-black/45 hover:text-cyan-200"
          >
            Owner Console →
          </Link>
          <Link
            href="/ops"
            className="rounded-xl border border-cyan-400 bg-black/35 px-4 py-2 text-slate-300 backdrop-blur-xl transition hover:bg-black/45 hover:text-cyan-200"
          >
            Ops Console →
          </Link>
          <Link
            href="/platform-readiness"
            className="rounded-xl border border-white/10 bg-black/35 px-4 py-2 text-slate-300 backdrop-blur-xl transition hover:bg-black/45 hover:text-cyan-200"
          >
            Platform Readiness →
          </Link>
        </section>
      </div>
    </main>
  );
}
