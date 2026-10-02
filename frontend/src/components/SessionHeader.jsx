import React, { useState } from 'react';
import { ShieldCheck, RefreshCw, PlusCircle, CheckCircle, Database } from 'lucide-react';
import { reloadSOPs } from '../api';

export default function SessionHeader({ threadId, onResetSession, health }) {
  const [reloading, setReloading] = useState(false);
  const [reloadMsg, setReloadMsg] = useState(null);

  const handleReloadSOPs = async () => {
    try {
      setReloading(true);
      const res = await reloadSOPs();
      setReloadMsg(`Reloaded ${res.count} SOPs`);
      setTimeout(() => setReloadMsg(null), 3000);
    } catch (e) {
      setReloadMsg(`Reload failed: ${e.message}`);
      setTimeout(() => setReloadMsg(null), 3000);
    } finally {
      setReloading(false);
    }
  };

  return (
    <header className="bg-slate-900/90 border-b border-slate-800/80 backdrop-blur-md px-4 py-3 sticky top-0 z-30 shadow-md">
      <div className="max-w-5xl mx-auto flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 to-blue-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <ShieldCheck className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-base text-slate-100 flex items-center gap-2">
              Outdoor Peer Guardian
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-cyan-950/80 text-cyan-400 border border-cyan-800/60">
                Helpful · Soft · Live Weather
              </span>
            </h1>
            <div className="text-xs text-slate-400 flex items-center gap-2">
              <span>Session: <code className="text-cyan-300 font-mono text-[11px]">{threadId.slice(0, 8)}...</code></span>
              <span>·</span>
              <span className="flex items-center gap-1 text-emerald-400">
                <CheckCircle className="w-3 h-3" />
                {health?.loaded_sops_count || 12} SOPs Active
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {reloadMsg && (
            <span className="text-xs text-emerald-300 bg-emerald-950/60 border border-emerald-800 px-2 py-1 rounded-lg animate-fadeIn">
              {reloadMsg}
            </span>
          )}

          <button
            onClick={handleReloadSOPs}
            disabled={reloading}
            title="Demonstrate dynamic 11th SOP update without server reboot"
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-200 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-all disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${reloading ? 'animate-spin' : ''}`} />
            <span>Hot Reload SOPs</span>
          </button>

          <button
            onClick={onResetSession}
            title="Start clean new session"
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-lg shadow-sm transition-all"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>New Session</span>
          </button>
        </div>
      </div>
    </header>
  );
}
