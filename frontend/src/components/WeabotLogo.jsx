import React from 'react';

export default function WeabotLogo({ className = "w-8 h-8 rounded-xl", iconOnly = false }) {
  return (
    <div className={`relative overflow-hidden flex items-center justify-center bg-gradient-to-tr from-purple-100 to-indigo-50 border border-purple-200/80 shadow-2xs select-none shrink-0 ${className}`}>
      <img
        src="/weabot-logo.png"
        alt="Weabot"
        className="w-full h-full object-cover"
        onError={(e) => {
          // If image fails, fallback to SVG bot with cloud
          e.target.style.display = 'none';
          e.target.nextSibling.style.display = 'flex';
        }}
      />
      {/* Crisp Vector Fallback: Bot with Cloud */}
      <div className="hidden w-full h-full items-center justify-center text-purple-700">
        <svg className="w-4 h-4 fill-purple-700" viewBox="0 0 24 24">
          <path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM12 9a2 2 0 0 1 2 2v2a2 2 0 0 1-4 0v-2a2 2 0 0 1 2-2zm-3 8a1 1 0 1 1 0-2 1 1 0 0 1 0 2zm6 0a1 1 0 1 1 0-2 1 1 0 0 1 0 2z"/>
        </svg>
      </div>
    </div>
  );
}
