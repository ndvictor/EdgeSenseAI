"use client";

import { useEffect, useState } from "react";
import { api, type AccountRiskProfile } from "@/lib/api";
import { MetricCard, PageHeader } from "@/components/Cards";

export default function AccountRiskPage() {
  const [profile, setProfile] = useState<AccountRiskProfile | null>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    api.getAccountRisk().then(setProfile);
  }, []);

  async function save() {
    if (!profile) return;
    const updated = await api.updateAccountRisk(profile);
    setProfile(updated);
    setMessage("Risk profile updated for agents and recommendations.");
  }

  if (!profile) return <div className="p-6 text-slate-400">Loading...</div>;

  return (
    <div className="p-6">
      <PageHeader eyebrow="account-aware control" title="Account Risk Center" description="Source of truth for small-account buying power, risk per trade, max position size, and minimum reward/risk." />
      <div className="mb-6 grid grid-cols-1 gap-4 xl:grid-cols-4">
        <MetricCard label="Buying Power" value={`$${profile.buying_power.toLocaleString()}`} accent />
        <MetricCard label="Account Equity" value={`$${profile.account_equity.toLocaleString()}`} />
        <MetricCard label="Cash" value={`$${profile.cash.toLocaleString()}`} />
        <MetricCard label="Min Reward/Risk" value={`${profile.min_reward_risk_ratio}R`} />
      </div>
      <div className="rounded-2xl border border-white/10 bg-slate-900/80 p-6">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <Field label="Account equity" value={profile.account_equity} onChange={(v) => setProfile({ ...profile, account_equity: v })} />
          <Field label="Buying power" value={profile.buying_power} onChange={(v) => setProfile({ ...profile, buying_power: v })} />
          <Field label="Cash" value={profile.cash} onChange={(v) => setProfile({ ...profile, cash: v })} />
          <Field label="Max risk trade percent" value={profile.max_risk_per_trade_percent} onChange={(v) => setProfile({ ...profile, max_risk_per_trade_percent: v })} />
          <Field label="Max daily loss percent" value={profile.max_daily_loss_percent} onChange={(v) => setProfile({ ...profile, max_daily_loss_percent: v })} />
          <Field label="Max position size percent" value={profile.max_position_size_percent} onChange={(v) => setProfile({ ...profile, max_position_size_percent: v })} />
          <Field label="Minimum R multiple" value={profile.min_reward_risk_ratio} onChange={(v) => setProfile({ ...profile, min_reward_risk_ratio: v })} />
        </div>
        <button onClick={save} className="mt-6 rounded-xl bg-cyan-400 px-5 py-3 font-black text-slate-950">Save risk settings</button>
        {message && <p className="mt-4 text-sm text-emerald-300">{message}</p>}
      </div>
    </div>
  );
}

function Field({ label, value, onChange }: { label: string; value: number; onChange: (value: number) => void }) {
  return (
    <label className="block">
      <span className="text-sm font-semibold text-slate-300">{label}</span>
      <input className="mt-2 w-full rounded-xl border border-white/10 bg-slate-950 px-4 py-3 text-white" type="number" value={value} onChange={(e) => onChange(Number(e.target.value))} />
    </label>
  );
}
