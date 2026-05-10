import Link from "next/link";

function accentBarClass(accent: string) {
  if (accent === "sky") return "bg-sky-400/90";
  if (accent === "violet") return "bg-violet-400/90";
  return "bg-cyan-400/90";
}

export default function Home() {
  const cards = [
    {
      title: "Autonomous Day-Trading Workflow",
      subtitle: "Paper-first, day-trading-only autonomous agent workflow.",
      badges: ["US stocks only", "Day trading only", "Paper-first", "Human approval", "No broker submit"],
      cta: "Enter Workflow",
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
          <h1 className="max-w-xl text-xl font-black tracking-[-0.04em] text-cyan-400 lg:text-5xl">
            Choose the right trading workspace.
          </h1>
          <p className="mt-4 max-w-3xl text-base leading-7 text-slate-400">
            Autonomous day-trading, legacy manual trading, and lab research are separate surfaces. The autonomous workflow remains paper-first,
            day-trading-only, and gated by human approval.
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
