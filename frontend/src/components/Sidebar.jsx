import React, { useState } from 'react';
import { 
  PanelLeftClose, 
  PanelLeft, 
  Plus, 
  Search, 
  Settings2, 
  ShieldCheck, 
  Trash2, 
  MessageSquare,
  Clock,
  Pencil,
  Check,
  X
} from 'lucide-react';

export default function Sidebar({ 
  onNewChat, 
  sessions = [],
  activeThreadId,
  onSelectSession,
  onDeleteSession,
  onClearAllSessions,
  userName = 'Aditya',
  onUpdateUserName,
  onOpenSettings,
  isCollapsed, 
  onToggleCollapse 
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [isEditingUser, setIsEditingUser] = useState(false);
  const [nameInput, setNameInput] = useState(userName);

  const handleSaveName = () => {
    const trimmed = nameInput.trim() || 'Aditya';
    onUpdateUserName(trimmed);
    setIsEditingUser(false);
  };

  // Filter real user sessions
  const filteredSessions = sessions.filter((s) =>
    (s.title || 'Untitled Session').toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Group real sessions by today / older
  const today = new Date().toDateString();
  const todaySessions = [];
  const olderSessions = [];

  filteredSessions.forEach((s) => {
    const sDate = s.createdAt ? new Date(s.createdAt).toDateString() : today;
    if (sDate === today) {
      todaySessions.push(s);
    } else {
      olderSessions.push(s);
    }
  });

  if (isCollapsed) {
    return (
      <aside className="w-16 bg-white border-r border-gray-100 flex flex-col items-center py-4 justify-between transition-all duration-300 shrink-0">
        <div className="flex flex-col items-center gap-4">
          <button
            onClick={onToggleCollapse}
            title="Expand Sidebar"
            className="w-10 h-10 rounded-xl bg-gray-50 hover:bg-gray-100 border border-gray-200/80 flex items-center justify-center text-gray-600 hover:text-gray-900 transition-all cursor-pointer"
          >
            <PanelLeft className="w-5 h-5" />
          </button>

          <button
            onClick={onNewChat}
            title="New Chat"
            className="w-10 h-10 rounded-xl bg-[#18181b] text-white flex items-center justify-center hover:bg-black transition-all shadow-xs cursor-pointer"
          >
            <Plus className="w-5 h-5" />
          </button>

          <button
            onClick={onOpenSettings}
            title="SOP Settings"
            className="w-10 h-10 rounded-xl bg-purple-50 text-purple-700 flex items-center justify-center hover:bg-purple-100 transition-all cursor-pointer"
          >
            <Settings2 className="w-5 h-5" />
          </button>
        </div>

        <div className="flex flex-col items-center gap-2">
          <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-purple-600 to-indigo-600 text-white font-bold text-sm flex items-center justify-center shadow-xs">
            {userName.charAt(0).toUpperCase()}
          </div>
        </div>
      </aside>
    );
  }

  return (
    <aside className="w-[270px] bg-white border-r border-gray-100 flex flex-col justify-between transition-all duration-300 shrink-0 select-none overflow-hidden h-full">
      {/* Top Header & Navigation */}
      <div className="flex flex-col p-4 pb-2">
        {/* Brand Bar without logo or green light */}
        <div className="flex items-center justify-between mb-3.5">
          <div className="flex items-center gap-2">
            <span className="font-bold text-[18px] text-gray-900 tracking-tight font-display">
              Weabot
            </span>
          </div>

          <button
            onClick={onToggleCollapse}
            title="Collapse sidebar"
            className="w-7 h-7 rounded-lg border border-gray-200 hover:bg-gray-100 flex items-center justify-center text-gray-400 hover:text-gray-700 transition-colors cursor-pointer"
          >
            <PanelLeftClose className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* "+ New chat" Button */}
        <button
          onClick={onNewChat}
          className="w-full h-10 bg-[#18181b] hover:bg-black text-white text-[13px] font-medium rounded-xl flex items-center justify-center gap-2 transition-all duration-150 shadow-xs active:scale-[0.99] mb-3 cursor-pointer"
        >
          <Plus className="w-4 h-4 stroke-[2.5]" />
          <span>New chat</span>
        </button>

        {/* Search Bar */}
        <div className="relative mb-2">
          <div className="flex items-center w-full bg-[#faf9fc] hover:bg-[#f4f2f9] focus-within:bg-white focus-within:ring-1 focus-within:ring-purple-300 border border-gray-200/90 rounded-xl px-2.5 py-1.5 transition-all text-xs">
            <Search className="w-3.5 h-3.5 text-gray-400 mr-2 shrink-0" />
            <input
              type="text"
              placeholder="Search conversations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-transparent border-none outline-none w-full text-xs text-gray-800 placeholder-gray-400"
            />
          </div>
        </div>

        {/* Primary Settings Link */}
        <button
          onClick={onOpenSettings}
          className="w-full flex items-center justify-between px-3 py-2 rounded-xl text-gray-700 hover:text-purple-900 hover:bg-purple-50/60 transition-all text-xs font-semibold cursor-pointer border border-transparent hover:border-purple-200"
        >
          <div className="flex items-center gap-2.5">
            <Settings2 className="w-4 h-4 text-purple-600" />
            <span>SOP Policy Studio</span>
          </div>
          <span className="text-[10px] text-purple-600 bg-purple-100 px-1.5 py-0.2 rounded font-medium">
            Edit SOPs
          </span>
        </button>
      </div>

      {/* Real Conversation History Section */}
      <div className="flex-1 overflow-y-auto px-4 py-1 text-xs space-y-3">
        {sessions.length === 0 ? (
          <div className="text-center py-10 px-2 text-gray-400 text-xs">
            <Clock className="w-6 h-6 mx-auto mb-2 opacity-40 text-purple-400" />
            <p className="font-medium text-gray-600">No session history yet</p>
            <p className="text-[11px] mt-1 text-gray-400">
              Inquiries you make will be preserved here.
            </p>
          </div>
        ) : (
          <>
            {/* Header with Clear All option */}
            {onClearAllSessions && (
              <div className="flex items-center justify-between px-2 pt-1 pb-1">
                <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                  History ({filteredSessions.length})
                </span>
                <button
                  onClick={() => {
                    if (window.confirm("Clear all session history? This cannot be undone.")) {
                      onClearAllSessions();
                    }
                  }}
                  className="text-[10px] text-gray-400 hover:text-rose-600 transition-colors cursor-pointer font-medium"
                  title="Clear all chat history"
                >
                  Clear all
                </button>
              </div>
            )}

            {todaySessions.length > 0 && (
              <div>
                <div className="text-[11px] font-semibold text-gray-400 px-2 py-1 uppercase tracking-wider">
                  Today
                </div>
                <div className="space-y-0.5">
                  {todaySessions.map((s) => {
                    const isActive = s.id === activeThreadId;
                    return (
                      <div
                        key={s.id}
                        className={`group flex items-center justify-between px-2.5 py-1.5 rounded-xl transition-all cursor-pointer ${
                          isActive
                            ? 'bg-purple-50 text-purple-950 font-semibold'
                            : 'text-gray-700 hover:bg-gray-50'
                        }`}
                      >
                        <button
                          onClick={() => onSelectSession(s)}
                          className="flex-1 text-left truncate text-[12px] flex items-center gap-2 cursor-pointer"
                          title={s.title}
                        >
                          <MessageSquare className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-purple-600' : 'text-gray-400'}`} />
                          <span className="truncate">{s.title || 'Untitled Session'}</span>
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onDeleteSession(s.id);
                          }}
                          title="Delete session"
                          className={`p-1 text-gray-400 hover:text-rose-600 rounded transition-opacity cursor-pointer ${
                            isActive ? 'opacity-80 hover:opacity-100' : 'opacity-0 group-hover:opacity-100'
                          }`}
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {olderSessions.length > 0 && (
              <div>
                <div className="text-[11px] font-semibold text-gray-400 px-2 py-1 uppercase tracking-wider">
                  Previous Days
                </div>
                <div className="space-y-0.5">
                  {olderSessions.map((s) => {
                    const isActive = s.id === activeThreadId;
                    return (
                      <div
                        key={s.id}
                        className={`group flex items-center justify-between px-2.5 py-1.5 rounded-xl transition-all cursor-pointer ${
                          isActive
                            ? 'bg-purple-50 text-purple-950 font-semibold'
                            : 'text-gray-700 hover:bg-gray-50'
                        }`}
                      >
                        <button
                          onClick={() => onSelectSession(s)}
                          className="flex-1 text-left truncate text-[12px] flex items-center gap-2 cursor-pointer"
                          title={s.title}
                        >
                          <MessageSquare className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-purple-600' : 'text-gray-400'}`} />
                          <span className="truncate">{s.title || 'Untitled Session'}</span>
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onDeleteSession(s.id);
                          }}
                          title="Delete session"
                          className={`p-1 text-gray-400 hover:text-rose-600 rounded transition-opacity cursor-pointer ${
                            isActive ? 'opacity-80 hover:opacity-100' : 'opacity-0 group-hover:opacity-100'
                          }`}
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* User Profile Footer (Editable Name, Default Aditya) */}
      <div className="p-3 border-t border-gray-100 bg-white">
        {isEditingUser ? (
          <div className="flex items-center gap-1.5 p-1">
            <input
              type="text"
              value={nameInput}
              onChange={(e) => setNameInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSaveName()}
              autoFocus
              className="flex-1 px-2 py-1 text-xs border border-purple-300 rounded-lg outline-none"
            />
            <button
              onClick={handleSaveName}
              className="p-1 rounded-md bg-purple-100 hover:bg-purple-200 text-purple-700"
            >
              <Check className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setIsEditingUser(false)}
              className="p-1 rounded-md hover:bg-gray-100 text-gray-400"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          <div className="flex items-center justify-between p-2 rounded-2xl hover:bg-gray-50 transition-colors">
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-purple-600 to-indigo-600 text-white font-bold text-xs flex items-center justify-center shrink-0 shadow-2xs">
                {userName.charAt(0).toUpperCase()}
              </div>
              <div className="truncate">
                <div className="text-[12px] font-semibold text-gray-900 leading-tight">
                  {userName}
                </div>
                <div className="text-[10px] text-gray-400 truncate">
                  Outdoor Safety User
                </div>
              </div>
            </div>

            <button
              onClick={() => {
                setNameInput(userName);
                setIsEditingUser(true);
              }}
              title="Edit Profile Name"
              className="p-1.5 text-gray-400 hover:text-purple-700 hover:bg-purple-50 rounded-lg transition-colors cursor-pointer"
            >
              <Pencil className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}
