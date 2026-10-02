import React, { useState } from 'react';
import HeroOrb from './HeroOrb';
import { Pencil, Check } from 'lucide-react';

export default function HeroGreeting({ userName = 'Aditya', onUpdateUserName }) {
  const [isEditing, setIsEditing] = useState(false);
  const [nameInput, setNameInput] = useState(userName);

  const handleSave = () => {
    const trimmed = nameInput.trim() || 'Aditya';
    onUpdateUserName(trimmed);
    setIsEditing(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleSave();
    } else if (e.key === 'Escape') {
      setNameInput(userName);
      setIsEditing(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center text-center pt-0 pb-1.5 select-none animate-fadeIn">
      {/* 3D Floating Pearlescent Lavender Orb */}
      <HeroOrb />

      {/* Greeting Title with Editable Name */}
      <div className="flex items-center justify-center gap-1.5 mb-1 group">
        {isEditing ? (
          <div className="flex items-center gap-1.5 bg-white border border-purple-300 rounded-xl px-2 py-0.5 shadow-xs">
            <span className="text-base sm:text-lg font-medium text-[#9d7fe6]">Hello,</span>
            <input
              type="text"
              value={nameInput}
              onChange={(e) => setNameInput(e.target.value)}
              onKeyDown={handleKeyDown}
              autoFocus
              className="text-base sm:text-lg font-medium text-gray-900 outline-none w-28 border-b border-purple-400 bg-transparent"
            />
            <button
              onClick={handleSave}
              className="p-1 rounded-md bg-purple-100 hover:bg-purple-200 text-purple-700 transition-colors"
              title="Save Name"
            >
              <Check className="w-3 h-3" />
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-1.5">
            <h2 className="text-base sm:text-lg font-medium tracking-tight text-[#9d7fe6]">
              Hello, <span className="text-gray-900 font-semibold">{userName}</span>
            </h2>
            <button
              onClick={() => {
                setNameInput(userName);
                setIsEditing(true);
              }}
              title="Edit Name"
              className="p-1 text-gray-400 hover:text-purple-600 rounded-lg hover:bg-purple-50 transition-all opacity-0 group-hover:opacity-100 cursor-pointer"
            >
              <Pencil className="w-3 h-3" />
            </button>
          </div>
        )}
      </div>

      {/* Subtitle / Question */}
      <h1 className="text-2xl sm:text-3xl md:text-[32px] font-bold text-gray-900 tracking-[-0.03em] leading-tight max-w-lg">
        How can I assist you today?
      </h1>
    </div>
  );
}
