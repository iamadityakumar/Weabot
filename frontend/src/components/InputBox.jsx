import React, { useState, useRef, useEffect } from 'react';
import { 
  Lightbulb, 
  Send,
  Bot,
  ChevronUp,
  Check
} from 'lucide-react';

export default function InputBox({ 
  onSendMessage, 
  disabled,
  selectedModel = 'Gemini 3.8 Flash',
  availableModels = [],
  onSelectModel
}) {
  const [text, setText] = useState('');
  const [isModelDropdownOpen, setIsModelDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);
  const textareaRef = useRef(null);

  // Close model dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsModelDropdownOpen(false);
      }
    }
    if (isModelDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('touchstart', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('touchstart', handleClickOutside);
    };
  }, [isModelDropdownOpen]);

  const handleSubmit = (e) => {
    e?.preventDefault();
    if (!text.trim() || disabled) return;
    onSendMessage(text.trim());
    setText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleTextChange = (e) => {
    setText(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 140)}px`;
    }
  };

  const modelList = availableModels.length > 0 ? availableModels : [
    { id: 'gemini-3.8-flash', name: 'Gemini 3.8 Flash', provider: 'Google DeepMind', tag: 'Fast & Grounded', color: 'text-purple-600 bg-purple-50' },
    { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro', provider: 'Google DeepMind', tag: 'High Reasoning', color: 'text-blue-600 bg-blue-50' },
    { id: 'qwen/qwen3.8-27b', name: 'Qwen 3.8 27B (Groq)', provider: 'Groq Cloud', tag: 'Ultra-Fast', color: 'text-emerald-600 bg-emerald-50' },
    { id: 'openai/gpt-oss-120b', name: 'GPT-OSS 120B (Groq)', provider: 'Groq Cloud', tag: 'Deep Reasoning', color: 'text-teal-600 bg-teal-50' },
    { id: 'open-meteo-deterministic', name: 'Open-Meteo Deterministic', provider: 'Safety Graph Engine', tag: 'Strict SOPs', color: 'text-rose-600 bg-rose-50' },
  ];

  return (
    <div className="w-full max-w-2xl mx-auto">
      {/* Floating Glassmorphism Input Shell */}
      <div className="bg-gradient-to-b from-white/95 via-white/85 to-white/80 hover:from-white/98 hover:to-white/90 focus-within:from-white focus-within:to-white/95 backdrop-blur-2xl rounded-3xl border border-white/85 shadow-[0_10px_30px_rgba(30,20,60,0.06),0_2px_8px_rgba(0,0,0,0.03)] focus-within:border-purple-300/80 focus-within:shadow-[0_16px_40px_rgba(147,51,234,0.12)] transition-all duration-300 p-2.5 sm:p-3.5 relative">
        {/* Text Input Area */}
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleTextChange}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder="Ask an outdoor activity safety question..."
          rows={1}
          className="w-full bg-transparent border-0 text-[14px] sm:text-[13.5px] text-gray-800 placeholder-gray-400 focus:ring-0 focus:outline-none resize-none leading-relaxed min-h-[36px] max-h-[140px] px-1"
        />

        {/* Bottom Action Row inside the card */}
        <div className="flex items-center justify-between pt-1.5 mt-1 border-t border-gray-100/70">
          {/* Left: Model Selector Dropdown & Sample Question Helper */}
          <div className="flex items-center gap-1.5 min-w-0">
            {/* Model Selector Pill Button */}
            <div className="relative" ref={dropdownRef}>
              <button
                type="button"
                onClick={() => setIsModelDropdownOpen(!isModelDropdownOpen)}
                title={`Current model: ${selectedModel}. Click to switch model.`}
                className="flex items-center gap-1.5 px-2 sm:px-2.5 py-1 text-xs font-medium text-gray-700 hover:text-purple-900 bg-purple-50/70 hover:bg-purple-100/80 border border-purple-200/70 rounded-lg transition-all cursor-pointer shadow-2xs active:scale-98 shrink-0"
              >
                <Bot className="w-3.5 h-3.5 text-purple-600 shrink-0" />
                <span className="max-w-[85px] sm:max-w-[130px] truncate font-medium text-[11px] sm:text-xs">
                  {selectedModel}
                </span>
                <ChevronUp className={`w-3 h-3 text-purple-500/80 shrink-0 transition-transform duration-200 ${isModelDropdownOpen ? 'rotate-180' : ''}`} />
              </button>

              {/* Upward Dropdown Menu */}
              {isModelDropdownOpen && (
                <div className="absolute bottom-full mb-2 left-0 w-72 sm:w-80 max-w-[calc(100vw-32px)] bg-white/95 backdrop-blur-xl border border-purple-200/80 rounded-2xl shadow-xl p-2 z-50 animate-fadeIn select-none">
                  <div className="px-2.5 py-1.5 border-b border-gray-100 flex items-center justify-between">
                    <span className="text-[11px] font-bold text-gray-800 uppercase tracking-wider font-mono">
                      Select AI Model
                    </span>
                    <span className="text-[10px] text-purple-600 font-medium bg-purple-50 px-1.5 py-0.5 rounded">
                      {modelList.length} Available
                    </span>
                  </div>

                  <div className="max-h-60 overflow-y-auto py-1 space-y-1">
                    {modelList.map((m) => {
                      const isSelected = selectedModel === m.name || selectedModel === m.id;
                      return (
                        <button
                          key={m.id || m.name}
                          type="button"
                          onClick={() => {
                            onSelectModel?.(m.name);
                            setIsModelDropdownOpen(false);
                          }}
                          className={`w-full text-left px-2.5 py-2 rounded-xl text-xs flex items-center justify-between transition-all cursor-pointer ${
                            isSelected
                              ? 'bg-purple-100/70 text-purple-950 font-semibold'
                              : 'hover:bg-purple-50/50 text-gray-700 hover:text-gray-950'
                          }`}
                        >
                          <div className="flex flex-col min-w-0 pr-2">
                            <div className="flex items-center gap-1.5">
                              <span className="truncate">{m.name}</span>
                              {m.tag && (
                                <span className="text-[9px] px-1.5 py-0.2 rounded bg-gray-100 text-gray-600 font-normal shrink-0">
                                  {m.tag}
                                </span>
                              )}
                            </div>
                            {m.provider && (
                              <span className="text-[10px] text-gray-400 font-normal mt-0.5">
                                {m.provider}
                              </span>
                            )}
                          </div>
                          {isSelected && (
                            <Check className="w-3.5 h-3.5 text-purple-600 shrink-0 stroke-[2.5]" />
                          )}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* Quick Idea Sample Question */}
            <button
              type="button"
              onClick={() => setText('What are the official high-wind safety guidelines for cycling?')}
              title="Insert sample safety question"
              className="flex items-center gap-1 px-1.5 sm:px-2 py-1 text-gray-400 hover:text-gray-700 hover:bg-gray-100/80 rounded-lg transition-colors cursor-pointer text-xs shrink-0"
            >
              <Lightbulb className="w-3.5 h-3.5 text-amber-500/80 shrink-0" />
              <span className="text-[11px] hidden sm:inline text-gray-500">Sample question</span>
            </button>
          </div>

          {/* Right: Send Button */}
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={handleSubmit}
              disabled={!text.trim() || disabled}
              title="Send message (Enter)"
              className={`w-7 h-7 sm:w-8 sm:h-8 rounded-full flex items-center justify-center transition-all duration-200 shadow-xs active:scale-95 cursor-pointer ${
                text.trim().length > 0 && !disabled
                  ? 'bg-[#18181b] hover:bg-black text-white shadow-purple-200'
                  : 'bg-gray-100 text-gray-400 cursor-not-allowed opacity-60'
              }`}
            >
              <Send className="w-3 h-3 sm:w-3.5 sm:h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
