import React from 'react';
import { X, Sparkles, ArrowRight } from 'lucide-react';

export default function SavedPromptsModal({ isOpen, onClose, onSelectPrompt }) {
  if (!isOpen) return null;

  const promptCategories = [
    {
      category: 'Outdoor & Weather Safety',
      prompts: [
        'Is it safe to go cycling in Chicago right now?',
        'Can I take my toddler to the playground at 1 PM in LA?',
        'Thinking of pedaling two wheels to the office this morning in Bhopal',
        'Will my grandpa be ok to go for exercise at 3pm in Mumbai?',
        'My 75-year-old grandma wants to take a morning walk in Ottawa',
      ],
    },
    {
      category: 'Hazard, Trail & Flight Operations',
      prompts: [
        'Check wind gusts and trail safety for an afternoon hike in Seattle',
        'What wind gust threshold halts outdoor drone photography operations?',
        'Are there severe weather or lightning warnings active for Denver right now?',
        'Check if heat index and UV conditions are safe for a midday run in Phoenix',
      ],
    },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/35 backdrop-blur-xs animate-fadeIn">
      <div className="bg-white rounded-3xl max-w-lg w-full p-6 shadow-2xl border border-gray-100 relative animate-fadeIn max-h-[85vh] flex flex-col">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-full transition-colors"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Header */}
        <div className="flex items-center gap-2 mb-1">
          <Sparkles className="w-5 h-5 text-purple-600" />
          <h3 className="font-bold text-lg text-gray-900 font-display">Saved Prompts</h3>
        </div>
        <p className="text-xs text-gray-500 mb-4">
          Click any prompt to instantly run or edit it in Weabot.
        </p>

        {/* Prompts list */}
        <div className="overflow-y-auto space-y-4 pr-1">
          {promptCategories.map((cat, i) => (
            <div key={i}>
              <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
                {cat.category}
              </div>
              <div className="space-y-1.5">
                {cat.prompts.map((p, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      onSelectPrompt(p);
                      onClose();
                    }}
                    className="w-full text-left p-2.5 rounded-xl hover:bg-purple-50/70 border border-gray-100 hover:border-purple-200 transition-all flex items-center justify-between group cursor-pointer"
                  >
                    <span className="text-xs text-gray-700 group-hover:text-purple-900 font-medium">
                      {p}
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 text-gray-300 group-hover:text-purple-600 shrink-0 ml-2 transition-transform group-hover:translate-x-0.5" />
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
