import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import TopNavBar from './components/TopNavBar';
import ChatThread from './components/ChatThread';
import FooterBar from './components/FooterBar';
import HelpModal from './components/HelpModal';
import SavedPromptsModal from './components/SavedPromptsModal';
import SOPManagementModal from './components/SOPManagementModal';
import { 
  sendChatMessage, 
  getHealth, 
  getAvailableModels, 
  getChatSession, 
  syncChatSession 
} from './api';

function getInitialThreadId() {
  if (typeof window !== 'undefined') {
    const urlParams = new URLSearchParams(window.location.search);
    const chatFromUrl = urlParams.get('chat') || urlParams.get('session');
    if (chatFromUrl) return chatFromUrl;
  }
  const stored = sessionStorage.getItem('cortex_thread_id');
  if (stored) return stored;
  const newId = (typeof crypto !== 'undefined' && crypto.randomUUID) 
    ? crypto.randomUUID() 
    : 'session-' + Math.random().toString(36).substring(2, 11);
  sessionStorage.setItem('cortex_thread_id', newId);
  return newId;
}

function loadSavedSessions() {
  try {
    const raw = localStorage.getItem('cortex_sessions');
    if (!raw) return [];
    return JSON.parse(raw);
  } catch (e) {
    console.error('Failed to parse saved sessions:', e);
    return [];
  }
}

export default function App() {
  const [threadId, setThreadId] = useState(getInitialThreadId);
  const [messages, setMessages] = useState([]);
  const [sessions, setSessions] = useState(loadSavedSessions);
  const [loading, setLoading] = useState(false);
  const [health, setHealth] = useState(null);
  const [availableModels, setAvailableModels] = useState([]);

  // User name (default Aditya, editable)
  const [userName, setUserName] = useState(() => {
    return localStorage.getItem('cortex_user_name') || 'Aditya';
  });

  // Selected LLM Model
  const [selectedModel, setSelectedModel] = useState(() => {
    return localStorage.getItem('cortex_selected_model') || 'Gemini 3.8 Flash';
  });

  // Layout and modal states
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isHelpOpen, setIsHelpOpen] = useState(false);
  const [isSavedPromptsOpen, setIsSavedPromptsOpen] = useState(false);

  const fetchHealth = () => {
    getHealth()
      .then((data) => setHealth(data))
      .catch((err) => console.warn('Could not fetch health status:', err));
  };

  // Sync browser URL whenever active threadId changes
  useEffect(() => {
    if (threadId) {
      sessionStorage.setItem('cortex_thread_id', threadId);
      const url = new URL(window.location.href);
      if (url.searchParams.get('chat') !== threadId) {
        url.searchParams.set('chat', threadId);
        window.history.replaceState(null, '', url.toString());
      }
    }
  }, [threadId]);

  // Initial load: Fetch health, available models, and load shared chat if URL param present
  useEffect(() => {
    fetchHealth();
    
    getAvailableModels()
      .then((data) => {
        if (data && data.models && data.models.length > 0) {
          setAvailableModels(data.models);
          // If stored model is not in available models, reset to first available
          setSelectedModel((prev) => {
            const modelExists = data.models.some((m) => m.name === prev);
            if (!modelExists) {
              const defaultModel = data.models.find((m) => m.is_default) || data.models[0];
              localStorage.setItem('cortex_selected_model', defaultModel.name);
              return defaultModel.name;
            }
            return prev;
          });
        }
      })
      .catch((err) => console.warn('Could not fetch available models:', err));

    // Handle shared chat URL loading
    const urlParams = new URLSearchParams(window.location.search);
    const chatFromUrl = urlParams.get('chat') || urlParams.get('session');
    if (chatFromUrl) {
      const localSession = sessions.find((s) => s.id === chatFromUrl);
      if (localSession && localSession.messages && localSession.messages.length > 0) {
        setMessages(localSession.messages);
      } else {
        // Fetch shared session from server
        getChatSession(chatFromUrl)
          .then((data) => {
            if (data && data.messages && data.messages.length > 0) {
              setMessages(data.messages);
              if (data.model) setSelectedModel(data.model);
              setSessions((prev) => {
                if (prev.some((s) => s.id === chatFromUrl)) return prev;
                const newSess = {
                  id: chatFromUrl,
                  title: data.title || (data.messages[0]?.text?.slice(0, 42) + '...'),
                  createdAt: data.created_at || new Date().toISOString(),
                  updatedAt: data.updated_at || new Date().toISOString(),
                  messages: data.messages,
                };
                const updated = [newSess, ...prev];
                localStorage.setItem('cortex_sessions', JSON.stringify(updated));
                return updated;
              });
            }
          })
          .catch((err) => console.warn('Could not load shared session:', err));
      }
    }
  }, []);

  const handleUpdateUserName = (newName) => {
    setUserName(newName);
    localStorage.setItem('cortex_user_name', newName);
  };

  const handleSelectModel = (model) => {
    setSelectedModel(model);
    localStorage.setItem('cortex_selected_model', model);
  };

  // Persist sessions locally and sync with backend for persistent sharing
  const persistSession = (currentMessages, firstMessageText) => {
    if (currentMessages.length === 0) return;
    const title = firstMessageText.length > 42 ? firstMessageText.slice(0, 42) + '...' : firstMessageText;
    
    setSessions((prev) => {
      const existingIdx = prev.findIndex((s) => s.id === threadId);
      const sessionTitle = existingIdx >= 0 ? prev[existingIdx].title : title;

      const updatedSession = {
        id: threadId,
        title: sessionTitle,
        createdAt: existingIdx >= 0 ? prev[existingIdx].createdAt : new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        messages: currentMessages,
      };

      let newSessions;
      if (existingIdx >= 0) {
        newSessions = [...prev];
        newSessions[existingIdx] = updatedSession;
      } else {
        newSessions = [updatedSession, ...prev];
      }

      localStorage.setItem('cortex_sessions', JSON.stringify(newSessions));
      return newSessions;
    });

    // Sync to backend persistent store
    syncChatSession(threadId, title, selectedModel, currentMessages).catch(() => {});
  };

  const handleResetSession = () => {
    const newId = (typeof crypto !== 'undefined' && crypto.randomUUID) 
      ? crypto.randomUUID() 
      : 'session-' + Math.random().toString(36).substring(2, 11);
    sessionStorage.setItem('cortex_thread_id', newId);
    setThreadId(newId);
    setMessages([]);
    const url = new URL(window.location.href);
    url.searchParams.set('chat', newId);
    window.history.replaceState(null, '', url.toString());
  };

  const handleSelectSession = (session) => {
    sessionStorage.setItem('cortex_thread_id', session.id);
    setThreadId(session.id);
    setMessages(session.messages || []);
    const url = new URL(window.location.href);
    url.searchParams.set('chat', session.id);
    window.history.replaceState(null, '', url.toString());
  };

  const handleDeleteSession = (idToDelete) => {
    setSessions((prev) => {
      const updated = prev.filter((s) => s.id !== idToDelete);
      localStorage.setItem('cortex_sessions', JSON.stringify(updated));
      return updated;
    });
    if (threadId === idToDelete) {
      handleResetSession();
    }
  };

  const handleSendMessage = async (text) => {
    const userMsg = {
      id: 'msg-' + Date.now(),
      sender: 'user',
      text,
      timestamp: new Date().toISOString(),
    };

    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    persistSession(newMessages, text);
    setLoading(true);

    try {
      const data = await sendChatMessage(text, threadId, selectedModel);
      const botMsg = {
        id: 'msg-' + (Date.now() + 1),
        sender: 'advisor',
        text: data.response,
        sopCitations: data.sop_citations || [],
        weatherData: data.weather_data,
        sessionFacts: data.session_facts,
        verdict: data.verdict,
        modelUsed: data.model_used || selectedModel,
        timestamp: new Date().toISOString(),
      };
      const finalMessages = [...newMessages, botMsg];
      setMessages(finalMessages);
      persistSession(finalMessages, text);
    } catch (err) {
      const errorMsg = {
        id: 'msg-' + (Date.now() + 1),
        sender: 'advisor',
        text: `⚠️ **Service Error**: ${err.message}`,
        sopCitations: [],
        timestamp: new Date().toISOString(),
      };
      const finalMessages = [...newMessages, errorMsg];
      setMessages(finalMessages);
      persistSession(finalMessages, text);
    } finally {
      setLoading(false);
    }
  };



  // Determine active conversation title for the top bar
  const activeSession = sessions.find((s) => s.id === threadId);
  const currentChatTitle = activeSession?.title || (messages.length > 0 ? (messages[0]?.text?.slice(0, 48) + (messages[0]?.text?.length > 48 ? '...' : '')) : 'New chat');

  return (
    <div className="w-screen h-screen m-0 p-0 bg-white text-gray-900 flex flex-row overflow-hidden select-none">
      {/* Left Sidebar (Desktop) */}
      <div className="hidden md:flex h-full shrink-0">
        <Sidebar
          onNewChat={handleResetSession}
          sessions={sessions}
          activeThreadId={threadId}
          onSelectSession={handleSelectSession}
          onDeleteSession={handleDeleteSession}
          userName={userName}
          onUpdateUserName={handleUpdateUserName}
          onOpenSettings={() => setIsSettingsOpen(true)}
          isCollapsed={isSidebarCollapsed}
          onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        />
      </div>

      {/* Mobile Sidebar Overlay */}
      {isMobileSidebarOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex">
          <div 
            className="fixed inset-0 bg-black/30 backdrop-blur-xs"
            onClick={() => setIsMobileSidebarOpen(false)}
          />
          <div className="relative z-10 w-72 bg-white h-full shadow-2xl">
            <Sidebar
              onNewChat={() => {
                handleResetSession();
                setIsMobileSidebarOpen(false);
              }}
              sessions={sessions}
              activeThreadId={threadId}
              onSelectSession={(s) => {
                handleSelectSession(s);
                setIsMobileSidebarOpen(false);
              }}
              onDeleteSession={handleDeleteSession}
              userName={userName}
              onUpdateUserName={handleUpdateUserName}
              onOpenSettings={() => {
                setIsSettingsOpen(true);
                setIsMobileSidebarOpen(false);
              }}
              isCollapsed={false}
              onToggleCollapse={() => setIsMobileSidebarOpen(false)}
            />
          </div>
        </div>
      )}

      {/* Main Full-Screen Workspace */}
      <div className="flex-1 flex flex-col h-full bg-white overflow-hidden relative">
        {/* Top Bar with Chat Title & Share Button */}
        <TopNavBar
          title={currentChatTitle}
          onToggleMobileSidebar={() => setIsMobileSidebarOpen(true)}
          threadId={threadId}
        />

        {/* Central Workspace: Chat / Hero Greeting */}
        <ChatThread
          messages={messages}
          loading={loading}
          onSendMessage={handleSendMessage}
          onOpenSavedPrompts={() => setIsSavedPromptsOpen(true)}
          userName={userName}
          onUpdateUserName={handleUpdateUserName}
          selectedModel={selectedModel}
          availableModels={availableModels}
          onSelectModel={handleSelectModel}
        />

        {/* Bottom Footer Bar */}
        <FooterBar onOpenHelp={() => setIsHelpOpen(true)} />
      </div>

      {/* SOP Policy Studio & Settings Modal */}
      <SOPManagementModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        onSOPsUpdated={fetchHealth}
      />

      {/* Safety Documentation Help Modal */}
      <HelpModal
        isOpen={isHelpOpen}
        onClose={() => setIsHelpOpen(false)}
      />

      {/* Saved Prompts Modal */}
      <SavedPromptsModal
        isOpen={isSavedPromptsOpen}
        onClose={() => setIsSavedPromptsOpen(false)}
        onSelectPrompt={handleSendMessage}
      />
    </div>
  );
}
