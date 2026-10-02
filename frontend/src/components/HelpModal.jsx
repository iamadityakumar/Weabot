import React from 'react';
import { X, HelpCircle, Shield, Cloud, RefreshCw, Cpu } from 'lucide-react';

export default function HelpModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/35 backdrop-blur-xs animate-fadeIn">
      <div className="bg-white rounded-3xl max-w-lg w-full p-6 shadow-2xl border border-gray-100 relative animate-fadeIn max-h-[85vh] overflow-y-auto">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-full transition-colors"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-2 mb-2">
          <div className="w-7 h-7 rounded-xl bg-purple-100 flex items-center justify-center text-purple-700">
            <HelpCircle className="w-4 h-4" />
          </div>
          <h3 className="font-bold text-lg text-gray-900 font-display">About Weabot & Outdoor Guardian</h3>
        </div>

        <p className="text-xs text-gray-500 mb-4 leading-relaxed">
          Weabot combines state-of-the-art conversational AI with authoritative outdoor hazard evaluation powered by real-time Open-Meteo meteorological telemetry and peer-reviewed safety SOPs.
        </p>

        <div className="space-y-3 text-xs text-gray-700">
          <div className="p-3 bg-purple-50/50 rounded-2xl border border-purple-100">
            <div className="font-semibold text-purple-900 flex items-center gap-1.5 mb-1">
              <Cloud className="w-4 h-4 text-purple-600" />
              Live Open-Meteo Integration
            </div>
            Weather conditions (temperature, gusts, precipitation, UV) are fetched directly from official Open-Meteo feeds based on detected cities.
          </div>

          <div className="p-3 bg-purple-50/50 rounded-2xl border border-purple-100">
            <div className="font-semibold text-purple-900 flex items-center gap-1.5 mb-1">
              <Shield className="w-4 h-4 text-purple-600" />
              Traceable Safety SOP Citations
            </div>
            Whenever hazard criteria are triggered, official SOP codes (e.g. SOP-001, SOP-004) are cited in the response metadata footer.
          </div>

          <div className="p-3 bg-purple-50/50 rounded-2xl border border-purple-100">
            <div className="font-semibold text-purple-900 flex items-center gap-1.5 mb-1">
              <RefreshCw className="w-4 h-4 text-purple-600" />
              Dynamic Hot-Reloading
            </div>
            Safety guidelines can be updated or expanded dynamically via the `···` menu without restarting the server.
          </div>
        </div>

        <button
          onClick={onClose}
          className="w-full mt-5 py-2.5 bg-[#18181b] hover:bg-black text-white text-xs font-semibold rounded-xl transition-all"
        >
          Got it
        </button>
      </div>
    </div>
  );
}
