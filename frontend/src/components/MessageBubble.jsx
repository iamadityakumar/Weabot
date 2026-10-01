import React from 'react';
import SOPBadge from './SOPBadge';
import WeatherSnapshot from './WeatherSnapshot';
import { User, ShieldAlert, AlertTriangle, Info, CheckCircle2 } from 'lucide-react';

export default function MessageBubble({ message }) {
  const isUser = message.sender === 'user';
  const citations = message.sopCitations || [];
  const isNoMatch = message.text && message.text.includes('do not have specific policies');
  const isError = message.text && message.text.includes('Weather Service Error');

  if (isUser) {
    return (
      <div className="flex justify-end mb-4 animate-fadeIn">
        <div className="flex gap-2 max-w-[85%] sm:max-w-[75%] items-end flex-row-reverse">
          <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center shrink-0 shadow-md">
            <User className="w-4 h-4 text-white" />
          </div>
          <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-4 py-3 rounded-2xl rounded-tr-none shadow-md text-sm leading-relaxed whitespace-pre-wrap">
            {message.text}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start mb-6 animate-fadeIn">
      <div className="flex gap-3 max-w-[95%] sm:max-w-[85%] items-start">
        <div
          className={`w-9 h-9 rounded-full flex items-center justify-center shrink-0 shadow-md ${
            isError
              ? 'bg-rose-600 text-white'
              : isNoMatch
              ? 'bg-amber-600 text-white'
              : 'bg-emerald-600 text-white'
          }`}
        >
          {isError ? (
            <AlertTriangle className="w-5 h-5" />
          ) : isNoMatch ? (
            <Info className="w-5 h-5" />
          ) : (
            <ShieldAlert className="w-5 h-5" />
          )}
        </div>

        <div className="flex flex-col gap-2 w-full">
          {/* Status Header & Badges */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold tracking-wide text-slate-400">
              {isError ? 'Service Notice' : isNoMatch ? 'Honest Policy Fallback' : 'Safety Advisor'}
            </span>
            {citations.map((c) => (
              <SOPBadge key={c} sopId={c} />
            ))}
          </div>

          {/* Main Bubble Content */}
          <div
            className={`px-5 py-4 rounded-2xl rounded-tl-none shadow-lg text-sm leading-relaxed border whitespace-pre-wrap ${
              isError
                ? 'bg-rose-950/40 border-rose-800/60 text-rose-100'
                : isNoMatch
                ? 'bg-slate-900/80 border-amber-600/40 text-slate-200'
                : 'bg-slate-900/90 border-slate-700/70 text-slate-100'
            }`}
          >
            {message.text}
          </div>

          {/* Weather Snapshot Widget */}
          {message.weatherData && (
            <WeatherSnapshot
              weather={message.weatherData}
              sessionFacts={message.sessionFacts}
            />
          )}
        </div>
      </div>
    </div>
  );
}
