import React from 'react';

export default function HeroOrb() {
  return (
    <div className="relative flex items-center justify-center w-20 h-20 sm:w-24 sm:h-24 mx-auto mb-1.5 select-none pointer-events-auto group">
      {/* Outer ambient pulsing violet bloom */}
      <div 
        className="absolute w-28 h-28 sm:w-32 sm:h-32 rounded-full bg-purple-400/25 blur-xl animate-orb-pulse pointer-events-none transition-all duration-700 group-hover:bg-purple-400/40 group-hover:scale-110"
      />
      
      {/* Secondary softer warm lilac glow */}
      <div 
        className="absolute w-24 h-24 sm:w-26 sm:h-26 rounded-full bg-fuchsia-300/20 blur-lg pointer-events-none"
      />

      {/* Main 3D Pearlescent Sphere Container */}
      <div className="relative w-16 h-16 sm:w-20 sm:h-20 rounded-full animate-orb-float cursor-pointer transition-transform duration-500 group-hover:scale-105">
        {/* Base Sphere with Multi-Stop Fluid Radial Gradient */}
        <div 
          className="w-full h-full rounded-full shadow-[0_10px_25px_-4px_rgba(147,51,234,0.35),0_4px_10px_rgba(168,85,247,0.2)]"
          style={{
            background: 'radial-gradient(circle at 35% 30%, #ffffff 0%, #f3e8ff 18%, #d8b4fe 40%, #c084fc 60%, #a855f7 80%, #7e22ce 100%)',
          }}
        />

        {/* Inner Curved Specular Reflection (Top Left Crescent) */}
        <div 
          className="absolute inset-0 rounded-full pointer-events-none"
          style={{
            background: 'radial-gradient(circle at 30% 25%, rgba(255, 255, 255, 0.95) 0%, rgba(255, 255, 255, 0.6) 15%, rgba(255, 255, 255, 0) 45%)',
          }}
        />

        {/* Soft Organic Wave / Sheen Rim inside the Orb */}
        <div 
          className="absolute inset-1 rounded-full pointer-events-none opacity-70 animate-orb-sheen"
          style={{
            background: 'conic-gradient(from 180deg at 50% 50%, transparent 0deg, rgba(255, 255, 255, 0.6) 60deg, transparent 120deg, rgba(233, 213, 255, 0.4) 220deg, transparent 360deg)',
            mixBlendMode: 'overlay',
          }}
        />

        {/* Bottom-Right Soft Rim Glow */}
        <div 
          className="absolute inset-0 rounded-full pointer-events-none"
          style={{
            background: 'radial-gradient(circle at 75% 80%, rgba(255, 255, 255, 0.45) 0%, transparent 35%)',
          }}
        />

        {/* Subtle glass reflection outline */}
        <div className="absolute inset-0 rounded-full border border-white/40 pointer-events-none" />
      </div>
    </div>
  );
}
