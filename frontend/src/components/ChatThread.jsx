import React, { useRef, useEffect } from 'react';
import MessageBubble from './MessageBubble';
import HeroGreeting from './HeroGreeting';
import InputBox from './InputBox';
import SuggestionCards from './SuggestionCards';
import { Sparkles } from 'lucide-react';

export default function ChatThread({ 
  messages, 
  loading, 
  onSendMessage, 
  onOpenSavedPrompts,
  userName = 'Aditya',
  onUpdateUserName,
  selectedModel,
  availableModels,
  onSelectModel
}) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Landing / Hero State (When no messages have been sent yet)
  if (messages.length === 0) {
    return (
      <div className="flex-1 overflow-y-auto px-3 sm:px-4 py-2 sm:py-3 flex flex-col justify-center items-center select-none h-full">
        <div className="w-full max-w-3xl flex flex-col items-center justify-center my-auto">
          {/* Animated 3D Orb + Greeting */}
          <HeroGreeting userName={userName} onUpdateUserName={onUpdateUserName} />

          {/* Central Input Box */}
          <div className="w-full">
            <InputBox
              onSendMessage={onSendMessage}
              disabled={loading}
              selectedModel={selectedModel}
              availableModels={availableModels}
              onSelectModel={onSelectModel}
            />
          </div>

          {/* Suggestion Prompt Cards */}
          <SuggestionCards onSelectPrompt={onSendMessage} />
        </div>
      </div>
    );
  }

  // Active Conversation Thread with Floating Glassmorphism Input Bar
  return (
    <div className="relative flex-1 flex flex-col overflow-hidden h-full">
      {/* Scrollable messages container with generous bottom padding so content never gets covered */}
      <div 
        id="chat-messages-container"
        className="flex-1 overflow-y-auto px-3 sm:px-6 pt-3 sm:pt-4 pb-40 sm:pb-44 max-w-3xl mx-auto w-full scroll-smooth"
      >
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} userName={userName} />
        ))}

        {loading && (
          <div className="flex justify-start mb-4 animate-fadeIn">
            <div className="bg-white/90 backdrop-blur-md border border-[#eeecf5] px-3.5 py-2 rounded-2xl text-xs text-gray-500 shadow-2xs flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-purple-500 animate-ping" />
              <span>Assessing safety guidelines & live weather...</span>
            </div>
          </div>
        )}

        <div ref={bottomRef} className="h-4" />
      </div>

      {/* Floating Glassmorphism Dock with subtle gradient shadow of the object */}
      <div className="absolute bottom-0 inset-x-0 pointer-events-none flex flex-col items-center justify-end pb-2.5 sm:pb-4 pt-6 bg-gradient-to-t from-white/20 via-transparent to-transparent transition-all z-20">
        <div className="w-full max-w-2xl px-2.5 sm:px-4 pointer-events-auto relative">
          {/* Subtle diffused gradient shadow of the floating object */}
          <div className="absolute -inset-x-2 -bottom-2 top-2 bg-gradient-to-b from-purple-500/[0.04] via-slate-900/[0.05] to-slate-900/[0.09] blur-xl rounded-[36px] pointer-events-none -z-10" />
          <div className="absolute -bottom-3 inset-x-12 h-8 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-slate-900/[0.09] via-slate-900/[0.03] to-transparent blur-md rounded-full pointer-events-none -z-10" />

          <InputBox
            onSendMessage={onSendMessage}
            disabled={loading}
            selectedModel={selectedModel}
            availableModels={availableModels}
            onSelectModel={onSelectModel}
          />
        </div>
      </div>
    </div>
  );
}
