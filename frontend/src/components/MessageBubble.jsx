import React, { useState } from 'react';
import SOPBadge from './SOPBadge';
import VerdictWeatherCard from './VerdictWeatherCard';
import { 
  Sparkles, 
  Copy, 
  Check, 
  ThumbsUp, 
  ThumbsDown, 
  AlertTriangle, 
  ShieldCheck
} from 'lucide-react';

function renderFormattedText(text) {
  if (!text) return null;
  const paragraphs = text.split('\n\n');
  return paragraphs.map((para, pIdx) => {
    const lines = para.split('\n');
    return (
      <div key={pIdx} className={pIdx > 0 ? 'mt-1.5' : ''}>
        {lines.map((line, lIdx) => {
          const parts = line.split(/(\*\*.*?\*\*)/g);
          const renderedLine = parts.map((part, partIdx) => {
            if (part.startsWith('**') && part.endsWith('**')) {
              return (
                <strong key={partIdx} className="font-semibold text-gray-900">
                  {part.slice(2, -2)}
                </strong>
              );
            }
            return part;
          });

          return (
            <div key={lIdx} className={line.startsWith('•') || line.startsWith('-') ? 'pl-2 my-0.5' : ''}>
              {renderedLine}
            </div>
          );
        })}
      </div>
    );
  });
}

export default function MessageBubble({ message, userName = 'Aditya' }) {
  const isUser = message.sender === 'user';
  const citations = message.sopCitations || [];
  const isError = message.text && message.text.includes('Service Error');
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const handleCopy = () => {
    navigator.clipboard?.writeText(message.text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isUser) {
    return (
      <div className="flex justify-end mb-3.5 animate-fadeIn">
        <div className="bg-[#f3f0f9] text-gray-900 border border-[#e8e4f3] px-3.5 py-2.5 rounded-2xl rounded-tr-xs shadow-2xs text-[13.5px] leading-relaxed whitespace-pre-wrap max-w-[88%] sm:max-w-[75%]">
          {message.text}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start mb-3.5 animate-fadeIn">
      <div className="flex flex-col gap-1.5 w-full min-w-0">
        {/* Active SOP Badges (if any policy triggered) */}
        {citations.length > 0 && (
          <div className="flex flex-wrap items-center gap-1 mb-0.5">
            <span className="text-[10px] text-gray-400 font-medium">Applied SOPs:</span>
            {citations.map((c) => (
              <SOPBadge key={c} sopId={c} />
            ))}
          </div>
        )}

        {/* 1. Highlighted Verdict & Weather Master Card (Ultra-Compact, Dynamic) */}
        {message.weatherData && (
          <VerdictWeatherCard
            verdict={message.verdict}
            weather={message.weatherData}
            sessionFacts={message.sessionFacts}
            sopCitations={citations}
          />
        )}

        {/* 2. Main Guidance / Advice Bubble Content */}
        <div
          className={`p-3 sm:p-3.5 rounded-2xl rounded-tl-xs shadow-2xs text-[13.5px] leading-relaxed border transition-all ${
            isError
              ? 'bg-rose-50/70 border-rose-200 text-rose-900'
              : 'bg-white border-[#eeecf5] text-gray-800'
          }`}
        >
          {renderFormattedText(message.text)}
        </div>

          {/* Action Row: Copy, Feedback & Model Attribution */}
          <div className="flex items-center justify-between pl-0.5 pt-0.5 text-gray-400 text-[11px]">
            <div className="flex items-center gap-2">
              <button
                onClick={handleCopy}
                className="flex items-center gap-1 hover:text-gray-700 transition-colors p-1 rounded-md hover:bg-gray-100 cursor-pointer"
                title="Copy message text"
              >
                {copied ? (
                  <>
                    <Check className="w-3 h-3 text-emerald-600" />
                    <span className="text-[10px] text-emerald-600">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3" />
                    <span className="text-[10px]">Copy</span>
                  </>
                )}
              </button>

              <span className="text-gray-200">|</span>

              <button
                onClick={() => setFeedback(feedback === 'up' ? null : 'up')}
                className={`p-1 rounded-md transition-colors cursor-pointer ${
                  feedback === 'up' ? 'text-purple-600 bg-purple-50' : 'hover:text-gray-700 hover:bg-gray-100'
                }`}
                title="Helpful guidance"
              >
                <ThumbsUp className="w-3 h-3" />
              </button>

              <button
                onClick={() => setFeedback(feedback === 'down' ? null : 'down')}
                className={`p-1 rounded-md transition-colors cursor-pointer ${
                  feedback === 'down' ? 'text-rose-600 bg-rose-50' : 'hover:text-gray-700 hover:bg-gray-100'
                }`}
                title="Unhelpful"
              >
                <ThumbsDown className="w-3 h-3" />
              </button>
            </div>

            {/* Model Attribution Badge */}
            {message.modelUsed && (
              <div className="flex items-center gap-1 text-[10.5px] font-medium text-purple-700/80 bg-purple-50/80 border border-purple-200/60 px-2 py-0.5 rounded-full shadow-2xs">
                <Sparkles className="w-2.5 h-2.5 text-purple-500" />
                <span className="truncate max-w-[150px]">{message.modelUsed}</span>
              </div>
            )}
          </div>
      </div>
    </div>
  );
}
