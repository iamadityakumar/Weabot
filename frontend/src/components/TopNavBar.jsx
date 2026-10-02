import React, { useState } from 'react';
import { 
  Check, 
  Share2, 
  Menu
} from 'lucide-react';

export default function TopNavBar({ 
  title = 'New chat',
  onToggleMobileSidebar,
  threadId
}) {
  const [copiedLink, setCopiedLink] = useState(false);

  const handleCopyLink = () => {
    const shareUrl = `${window.location.origin}${window.location.pathname}?chat=${encodeURIComponent(threadId)}`;
    navigator.clipboard?.writeText(shareUrl);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2500);
  };

  return (
    <header className="h-12 sm:h-13 px-3 sm:px-5 border-b border-gray-100 flex items-center justify-between shrink-0 bg-white select-none relative z-20">
      {/* Left: Mobile hamburger menu trigger + Chat Title */}
      <div className="flex items-center min-w-0 pr-3">
        <button
          type="button"
          onClick={onToggleMobileSidebar}
          className="md:hidden p-1.5 -ml-1 mr-1 text-gray-600 hover:text-gray-900 rounded-lg hover:bg-gray-100 cursor-pointer shrink-0"
          title="Open Conversation History"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Title of the active chat */}
        <h1 
          className="text-xs sm:text-[13.5px] font-semibold text-gray-800 truncate max-w-[200px] sm:max-w-md md:max-w-lg" 
          title={title}
        >
          {title}
        </h1>
      </div>

      {/* Right: Share Button on top in the same position */}
      <div className="flex items-center shrink-0 ml-auto">
        <button
          type="button"
          onClick={handleCopyLink}
          title={copiedLink ? 'Unique chat URL copied to clipboard!' : 'Copy Shareable Link for this Chat'}
          className={`h-8 px-2.5 sm:px-3 rounded-xl border transition-all flex items-center gap-1.5 text-xs font-medium cursor-pointer shadow-2xs active:scale-95 ${
            copiedLink 
              ? 'border-emerald-300 bg-emerald-50 text-emerald-700' 
              : 'border-gray-200/90 hover:bg-gray-50 text-gray-600 hover:text-gray-900'
          }`}
        >
          {copiedLink ? <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0" /> : <Share2 className="w-3.5 h-3.5 shrink-0" />}
          <span className="hidden sm:inline">{copiedLink ? 'Copied' : 'Share'}</span>
        </button>
      </div>
    </header>
  );
}
