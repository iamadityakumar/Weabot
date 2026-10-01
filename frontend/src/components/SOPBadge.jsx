import React from 'react';

export default function SOPBadge({ sopId, title, severity = 'moderate' }) {
  const getBadgeStyle = (sev) => {
    switch (sev.toLowerCase()) {
      case 'high':
        return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'moderate':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      case 'low':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
      default:
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
    }
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${getBadgeStyle(
        severity
      )} tracking-wide transition-all`}
      title={title || sopId}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse"></span>
      {sopId}
      {title && <span className="opacity-75 font-normal ml-0.5 max-w-[200px] truncate">· {title}</span>}
    </span>
  );
}
