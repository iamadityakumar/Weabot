import React from 'react';
import { X, Check, Sparkles, Zap, Shield, Globe } from 'lucide-react';

export default function UpgradeModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs animate-fadeIn">
      <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-gray-100 relative animate-fadeIn">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-full transition-colors"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-2.5 mb-2">
          <div className="w-8 h-8 rounded-xl bg-purple-100 flex items-center justify-center text-purple-700">
            <Sparkles className="w-4 h-4 fill-purple-300 text-purple-700" />
          </div>
          <h3 className="font-bold text-lg text-gray-900 font-display">Upgrade to Cortex Pro</h3>
        </div>
        <p className="text-xs text-gray-500 mb-5 leading-relaxed">
          Unlock unlimited real-time Open-Meteo evaluations, custom safety policy graphs, and priority ultra-fast inference.
        </p>

        {/* Feature List */}
        <div className="space-y-3 mb-6">
          {[
            { icon: Zap, text: 'Unlimited multi-location hourly micro-forecasts' },
            { icon: Shield, text: 'Custom SOP policy ingestion & hot-reloading' },
            { icon: Globe, text: 'Extended multi-turn session memory retention' },
            { icon: Sparkles, text: 'Access to next-gen Cortex Reasoning models' },
          ].map((f, i) => {
            const Icon = f.icon;
            return (
              <div key={i} className="flex items-center gap-2.5 text-xs text-gray-700">
                <div className="w-5 h-5 rounded-md bg-purple-50 text-purple-600 flex items-center justify-center shrink-0">
                  <Check className="w-3.5 h-3.5" />
                </div>
                <span>{f.text}</span>
              </div>
            );
          })}
        </div>

        {/* Price & CTA */}
        <div className="p-3.5 rounded-2xl bg-[#faf9fe] border border-purple-100 mb-4 flex items-center justify-between">
          <div>
            <div className="text-[11px] text-gray-500 font-medium">Pro Monthly</div>
            <div className="text-xl font-bold text-gray-900">$20 <span className="text-xs font-normal text-gray-400">/ month</span></div>
          </div>
          <span className="text-[10px] font-semibold text-purple-700 bg-purple-100 px-2 py-0.5 rounded-full">
            Cancel anytime
          </span>
        </div>

        <button
          onClick={onClose}
          className="w-full py-2.5 bg-[#18181b] hover:bg-black text-white text-xs font-semibold rounded-xl transition-all shadow-md active:scale-[0.98]"
        >
          Get Cortex Pro
        </button>
      </div>
    </div>
  );
}
