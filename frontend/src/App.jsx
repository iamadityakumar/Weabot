import React, { useState, useEffect } from 'react';
import SessionHeader from './components/SessionHeader';
import ChatThread from './components/ChatThread';
import InputBox from './components/InputBox';
import { sendChatMessage, getHealth } from './api';

function getInitialThreadId() {
  const stored = sessionStorage.getItem('advisor_thread_id');
  if (stored) return stored;
  const newId = (typeof crypto !== 'undefined' && crypto.randomUUID) ? crypto.randomUUID() : 'session-' + Math.random().toString(36).substring(2, 11);
  sessionStorage.setItem('advisor_thread_id', newId);
  return newId;
}

export default function App() {
  const [threadId, setThreadId] = useState(getInitialThreadId);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [health, setHealth] = useState(null);

  useEffect(() => {
    getHealth()
      .then((data) => setHealth(data))
      .catch((err) => console.warn('Could not fetch health status:', err));
  }, []);

  const handleResetSession = () => {
    const newId = (typeof crypto !== 'undefined' && crypto.randomUUID) ? crypto.randomUUID() : 'session-' + Math.random().toString(36).substring(2, 11);
    sessionStorage.setItem('advisor_thread_id', newId);
    setThreadId(newId);
    setMessages([]);
  };

  const handleSendMessage = async (text) => {
    const userMsg = {
      id: 'msg-' + Date.now(),
      sender: 'user',
      text,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const data = await sendChatMessage(text, threadId);
      const botMsg = {
        id: 'msg-' + (Date.now() + 1),
        sender: 'advisor',
        text: data.response,
        sopCitations: data.sop_citations || [],
        weatherData: data.weather_data,
        sessionFacts: data.session_facts,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      const errorMsg = {
        id: 'msg-' + (Date.now() + 1),
        sender: 'advisor',
        text: `⚠️ **Service Error**: ${err.message}`,
        sopCitations: [],
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-slate-950 text-slate-100 font-sans antialiased selection:bg-cyan-500 selection:text-white">
      <SessionHeader
        threadId={threadId}
        onResetSession={handleResetSession}
        health={health}
      />
      <ChatThread messages={messages} loading={loading} />
      <InputBox onSendMessage={handleSendMessage} disabled={loading} />
    </div>
  );
}
