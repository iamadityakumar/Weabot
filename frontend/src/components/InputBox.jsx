import React, { useState, useRef, useEffect } from 'react';
import { Send, CornerDownLeft, Sparkles } from 'lucide-react';

export default function InputBox({ onSendMessage, disabled }) {
  const [text, setText] = useState('');
  const textareaRef = useRef(null);

  const samplePrompts = [
    'Is it safe to go cycling in Chicago right now?',
    'Can I take my toddler to the playground at 1 PM in LA?',
    'Thinking of pedaling two wheels to the office this morning in Bhopal',
    'Is it safe to fly my photography drone in the park?',
    'My 75-year-old grandma wants to take a morning walk in Ottawa',
  ];

  const handleSubmit = (e) => {
    e?.preventDefault();
    if (!text.trim() || disabled) return;
    onSendMessage(text.trim());
    setText('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handlePromptClick = (p) => {
    setText(p);
    textareaRef.current?.focus();
  };

  return (
    <div className="bg-slate-900/90 border-t border-slate-800/80 p-4 sticky bottom-0 z-20 backdrop-blur-md">
      <div className="max-w-5xl mx-auto">
        {/* Sample Prompt Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-2 mb-2 scrollbar-none text-[11px]">
          <span className="text-slate-500 flex items-center gap-1 shrink-0 font-medium">
            <Sparkles className="w-3 h-3 text-cyan-400" />
            Quick Try:
          </span>
          {samplePrompts.map((p, idx) => (
            <button
              key={idx}
              onClick={() => handlePromptClick(p)}
              disabled={disabled}
              className="shrink-0 bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 border border-slate-700/60 px-2.5 py-1 rounded-full transition-all text-left truncate max-w-[240px]"
            >
              {p}
            </button>
          ))}
        </div>

        {/* Input Form */}
        <form onSubmit={handleSubmit} className="flex gap-2 items-end">
          <div className="relative flex-1">
            <textarea
              ref={textareaRef}
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={disabled}
              placeholder="Ask an outdoor safety question (e.g., 'Is it safe to bike to work in Bhopal today?')..."
              rows={2}
              className="w-full bg-slate-950/80 border border-slate-700/80 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 resize-none outline-none transition-all"
            />
          </div>

          <button
            type="submit"
            disabled={!text.trim() || disabled}
            className="h-11 px-4 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-xl font-medium shadow-md shadow-cyan-600/20 disabled:opacity-40 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-1.5"
          >
            <Send className="w-4 h-4" />
            <span className="hidden sm:inline text-xs">Send</span>
          </button>
        </form>
      </div>
    </div>
  );
}
