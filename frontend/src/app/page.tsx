import Link from "next/link";

export default function Home() {
  return (
    <div className="p-6">
      <h1 className="text-3xl font-black text-white">EdgeSenseAI</h1>
      <p className="mt-2 text-slate-400">Small-account edge signal and recommendation platform.</p>
      <Link className="mt-6 inline-flex rounded-xl bg-emerald-500 px-4 py-2 font-bold text-white" href="/command-center">
        Open Command Center
      </Link>
    </div>
  );
}
