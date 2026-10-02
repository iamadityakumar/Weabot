import React from 'react';

export default function SOPBadge({ sopId, title, severity = 'moderate' }) {
  const getBadgeStyle = (sev) => {
    switch (sev.toLowerCase()) {
      case 'high':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'moderate':
        return 'bg-purple-50 text-purple-700 border-purple-200';
      case 'low':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      default:
        return 'bg-indigo-50 text-indigo-700 border-indigo-200';
    }
  };

  const getDotStyle = (sev) => {
    switch (sev.toLowerCase()) {
      case 'high':
        return 'bg-rose-500';
      case 'moderate':
        return 'bg-purple-500';
      case 'low':
        return 'bg-emerald-500';
      default:
        return 'bg-indigo-500';
    }
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${getBadgeStyle(
        severity
      )} tracking-wide transition-all shadow-2xs`}
      title={title || sopId}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${getDotStyle(severity)} animate-pulse`} />
      <span>{sopId}</span>
      {title && <span className="opacity-70 font-normal ml-0.5 max-w-[180px] truncate">· {title}</span>}
    </span>
  );
}
