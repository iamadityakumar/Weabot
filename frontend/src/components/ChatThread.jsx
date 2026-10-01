import React, { useRef, useEffect } from 'react';
import MessageBubble from './MessageBubble';
import { Shield, Sparkles } from 'lucide-react';

export default function ChatThread({ messages, loading }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 text-center text-slate-400">
        <div className="w-16 h-16 rounded-2xl bg-slate-800/80 border border-slate-700/60 flex items-center justify-center mb-4 text-cyan-400 shadow-xl">
          <Shield className="w-8 h-8" />
        </div>
        <h2 className="text-xl font-bold text-slate-200 mb-2">Outdoor Safety Advisor</h2>
        <p className="max-w-md text-sm text-slate-400 mb-6 leading-relaxed">
          Grounded exclusively in <strong>live Open-Meteo weather data</strong> and <strong>strict Standard Operating Procedures (SOPs)</strong>.
          Every answer is traceable to an official policy, or we honestly declare no guidance exists.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg text-left text-xs">
          <div className="p-3 bg-slate-900/60 border border-slate-800 rounded-xl">
            <span className="font-semibold text-slate-200 block mb-1">📍 Multi-Turn Session Memory</span>
            Follow-up questions remember your location ("what about this evening?") without re-prompting.
          </div>
          <div className="p-3 bg-slate-900/60 border border-slate-800 rounded-xl">
            <span className="font-semibold text-slate-200 block mb-1">🛡️ Traceable Policy Footers</span>
            Every response includes cited SOP IDs matching official operating procedures.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 max-w-5xl mx-auto w-full">
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}

      {loading && (
        <div className="flex justify-start mb-6 animate-pulse">
          <div className="flex gap-3 items-center">
            <div className="w-9 h-9 rounded-full bg-cyan-900/60 border border-cyan-700 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-cyan-400 animate-spin" />
            </div>
            <div className="bg-slate-900/80 border border-slate-800 px-4 py-3 rounded-2xl rounded-tl-none text-xs text-slate-400">
              Querying live weather & evaluating safety SOP graph...
            </div>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
