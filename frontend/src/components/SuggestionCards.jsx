import React from 'react';
import { Bike, ShieldAlert, HeartPulse, Mountain } from 'lucide-react';

export default function SuggestionCards({ onSelectPrompt }) {
  const cards = [
    {
      id: 'cycling',
      icon: Bike,
      title: 'Cycling & Wind Hazard',
      subtitle: 'Is it safe to go cycling in Chicago right now?',
      prompt: 'Is it safe to go cycling in Chicago right now?',
    },
    {
      id: 'toddler',
      icon: ShieldAlert,
      title: 'Playground & Heat Guard',
      subtitle: 'Can I take my toddler to the park in Los Angeles?',
      prompt: 'Can I take my toddler to the park at 1 PM in Los Angeles?',
    },
    {
      id: 'grandpa',
      icon: HeartPulse,
      title: 'Senior Exercise Safety',
      subtitle: 'Will my grandpa be ok to go for exercise at 3pm in Mumbai?',
      prompt: 'Will my grandpa be ok to go for exercise at 3pm in Mumbai?',
    },
    {
      id: 'hike',
      icon: Mountain,
      title: 'Trail & Ridge Weather',
      subtitle: 'Check wind gusts and trail safety for Seattle hike.',
      prompt: 'Check wind gusts and trail safety for an afternoon hike in Seattle',
    },
  ];

  return (
    <div className="w-full max-w-3xl mx-auto mt-2.5 sm:mt-3 animate-fadeIn">
      <div className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1.5 px-1">
        <span>Recommended Safety Inquiries</span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-2.5">
        {cards.map((card) => {
          const IconComp = card.icon;
          return (
            <button
              key={card.id}
              onClick={() => onSelectPrompt(card.prompt)}
              className="group text-left p-2.5 bg-white hover:bg-purple-50/40 border border-[#eeecf5] hover:border-purple-300 rounded-xl shadow-[0_2px_6px_rgba(0,0,0,0.02)] hover:shadow-[0_6px_16px_-4px_rgba(147,51,234,0.08)] transition-all duration-200 flex flex-col justify-between h-[78px] cursor-pointer"
            >
              <div className="w-5 h-5 flex items-center justify-center text-purple-600 group-hover:scale-110 transition-transform">
                <IconComp className="w-3.5 h-3.5 stroke-[1.8]" />
              </div>
              <div>
                <h4 className="text-[11.5px] font-semibold text-gray-900 group-hover:text-purple-950 leading-tight truncate">
                  {card.title}
                </h4>
                <p className="text-[10px] text-gray-500 leading-tight line-clamp-1 mt-0.5 font-normal group-hover:text-gray-600">
                  {card.subtitle}
                </p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
