import React from 'react';
import { ShieldCheck } from 'lucide-react';

export default function FooterBar({ onOpenHelp }) {
  return (
    <div className="w-full flex items-center justify-between px-4 py-1 text-[10.5px] select-none border-t border-gray-100/80 bg-white/90 shrink-0 relative">
      {/* Left indicator */}
      <div className="flex items-center gap-1.5 text-gray-400 text-[10.5px]">
        <ShieldCheck className="w-3 h-3 text-purple-600" />
        <span className="hidden sm:inline">Grounded in live Open-Meteo telemetry & verified safety SOPs</span>
      </div>

      {/* Right: Minimal Help Button */}
      <div className="flex items-center gap-2 shrink-0 ml-auto">
        <button
          onClick={onOpenHelp}
          title="Safety Documentation & Help"
          className="w-5 h-5 rounded-full border border-gray-200 hover:border-gray-300 hover:bg-gray-100 flex items-center justify-center text-gray-500 hover:text-gray-800 transition-all text-[10px] font-medium cursor-pointer"
        >
          ?
        </button>
      </div>
    </div>
  );
}
