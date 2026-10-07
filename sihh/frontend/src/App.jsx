import React, { useState, useRef, useEffect } from 'react';
import {
  Send, ThumbsUp, ThumbsDown, Mic, MicOff, Volume2, VolumeX,
  Copy, Check, RotateCw, Plus, Sparkles, Edit3,
  FileText, ExternalLink, Shield, ShieldCheck, ShieldAlert,
  Award, CheckCircle, Droplet, Smartphone, MessageSquarePlus,
  Database, Zap, ChevronDown, Settings, X
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import LatticeLoader from './LatticeLoader';
import ScraperPortal from './ScraperPortal';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [language, setLanguage] = useState('en');
  const [effort, setEffort] = useState('Medium');
  const [sessionId, setSessionId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [speakingIndex, setSpeakingIndex] = useState(null);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [loadingStartTime, setLoadingStartTime] = useState(null);
  const [langOpen, setLangOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [showScraper, setShowScraper] = useState(false);
  const [settings, setSettings] = useState({});
  const [tempLogoUrl, setTempLogoUrl] = useState('');

  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);
  const inputRef = useRef(null);

  const languages = [
    { value: 'en', label: 'English' },
    { value: 'hi', label: 'Hindi' },
    { value: 'ta', label: 'Tamil' },
    { value: 'te', label: 'Telugu' },
    { value: 'bn', label: 'Bengali' }
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => { scrollToBottom(); }, [messages, isLoading]);

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = language === 'hi' ? 'hi-IN' : 'en-US';
      recognition.onresult = (event) => {
        const transcript = Array.from(event.results).map(r => r[0].transcript).join('');
        setInput(transcript);
      };
      recognition.onend = () => setIsListening(false);
      recognition.onerror = () => setIsListening(false);
      recognitionRef.current = recognition;
    }
  }, [language]);

  useEffect(() => {
    fetch(`${API_BASE_URL}/settings`)
      .then(res => res.json())
      .then(data => {
        setSettings(data);
        setTempLogoUrl(data.logo_url || '');
      })
      .catch(err => console.error('Error fetching settings:', err));
  }, []);

  // Close lang dropdown on outside click
  useEffect(() => {
    if (!langOpen) return;
    const handler = (e) => {
      if (!e.target.closest('.lang-dropdown')) setLangOpen(false);
    };
    document.addEventListener('pointerdown', handler);
    return () => document.removeEventListener('pointerdown', handler);
  }, [langOpen]);

  const toggleListening = () => {
    if (!recognitionRef.current) return;
    if (isListening) { recognitionRef.current.stop(); setIsListening(false); }
    else { recognitionRef.current.start(); setIsListening(true); }
  };

  const speakText = (text, index) => {
    if (!('speechSynthesis' in window)) return;
    if (speakingIndex === index) { window.speechSynthesis.cancel(); setSpeakingIndex(null); return; }
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = language === 'hi' ? 'hi-IN' : 'en-US';
    u.onend = () => setSpeakingIndex(null);
    u.onerror = () => setSpeakingIndex(null);
    setSpeakingIndex(index);
    window.speechSynthesis.speak(u);
  };

  const copyToClipboard = (text, index) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const handleNewChat = () => {
    setMessages([]); setSessionId(null); setInput('');
    window.speechSynthesis?.cancel(); setSpeakingIndex(null);
  };

  const handleSend = async (customMessage = null) => {
    const textToSend = customMessage || input;
    if (!textToSend.trim()) return;

    const userMessage = { role: 'user', content: textToSend, origText: textToSend };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setLoadingStartTime(Date.now());

    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: textToSend, language, session_id: sessionId }),
      });
      const data = await response.json();
      if (!sessionId) setSessionId(data.session_id);
      const elapsed = Math.max(1, Math.floor((Date.now() - (loadingStartTime || Date.now())) / 1000));
      setMessages(prev => [...prev, {
        id: data.message_id, role: 'assistant', content: data.answer,
        citations: data.citations, confidence: data.confidence,
        queryContext: textToSend, thinkTime: elapsed,
      }]);
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'An error occurred while connecting to the server. Please check that the backend is running.'
      }]);
    } finally {
      setIsLoading(false);
      setLoadingStartTime(null);
    }
  };

  const handleRegenerate = async (lastUserText) => {
    if (!lastUserText || isLoading) return;
    setIsLoading(true); setLoadingStartTime(Date.now());
    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: lastUserText, language, session_id: sessionId }),
      });
      const data = await response.json();
      const elapsed = Math.max(1, Math.floor((Date.now() - (loadingStartTime || Date.now())) / 1000));
      setMessages(prev => [...prev, {
        id: data.message_id, role: 'assistant', content: data.answer,
        citations: data.citations, confidence: data.confidence,
        queryContext: lastUserText, thinkTime: elapsed,
      }]);
    } catch (error) { console.error('Error regenerating:', error); }
    finally { setIsLoading(false); setLoadingStartTime(null); }
  };

  const handleSaveSettings = async () => {
    try {
      await fetch(`${API_BASE_URL}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: 'logo_url', value: tempLogoUrl }),
      });
      setSettings(prev => ({ ...prev, logo_url: tempLogoUrl }));
      setSettingsOpen(false);
    } catch (error) {
      console.error('Error saving settings:', error);
    }
  };

  const handleFeedback = async (messageId, isPositive) => {
    try {
      await fetch(`${API_BASE_URL}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message_id: messageId, is_positive: isPositive }),
      });
    } catch (error) { console.error('Error submitting feedback:', error); }
  };

  const ConfidenceBadge = ({ confidence }) => {
    if (!confidence) return null;
    const config = {
      high: { icon: ShieldCheck, label: 'High confidence', cls: 'confidence-high' },
      medium: { icon: Shield, label: 'Medium confidence', cls: 'confidence-medium' },
      low: { icon: ShieldAlert, label: 'Low confidence', cls: 'confidence-low' },
    };
    const c = config[confidence] || config.medium;
    const Icon = c.icon;
    return (
      <span className={`confidence-badge ${c.cls}`} title={c.label}>
        <Icon size={12} /> {c.label}
      </span>
    );
  };

  const currentLang = languages.find(l => l.value === language);

  return (
    <div className="app-container">
      {/* Ambient Blobs */}
      <div className="ambient-blob blob-1" />
      <div className="ambient-blob blob-2" />

      {/* Header */}
      <header className="app-header">
        <div className="logo-section">
          {settings.logo_url ? (
            <img src={settings.logo_url} alt="Logo" style={{ height: '32px', borderRadius: '4px', marginRight: '8px' }} />
          ) : (
            <div className="logo-glow">
              <Sparkles className="sparkle-icon" size={22} />
            </div>
          )}
          <h1 className="logo-text">BIS Sahayak</h1>
          <span className="logo-badge">AI</span>
        </div>

        <div className="header-controls">
          {/* Effort Selector */}
          <div className="effort-selector">
            {['Low', 'Medium', 'High'].map(level => (
              <button
                key={level}
                className={`effort-btn ${effort === level ? 'active' : ''}`}
                onClick={() => setEffort(level)}
              >
                {level === 'High' && <Zap size={12} />}
                {level}
              </button>
            ))}
          </div>

          {/* Language Dropdown */}
          <div className="lang-dropdown">
            <button className="lang-trigger" onClick={() => setLangOpen(!langOpen)}>
              <span>{currentLang?.label}</span>
              <ChevronDown size={14} className={`chevron ${langOpen ? 'open' : ''}`} />
            </button>
            {langOpen && (
              <div className="lang-menu">
                {languages.map(lang => (
                  <button
                    key={lang.value}
                    className={`lang-option ${language === lang.value ? 'selected' : ''}`}
                    onClick={() => { setLanguage(lang.value); setLangOpen(false); }}
                  >
                    {lang.label}
                    {language === lang.value && <Check size={14} />}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* New Chat */}
          <button className="new-chat-btn" onClick={handleNewChat} title="New Chat" style={{ marginRight: '8px' }}>
            <MessageSquarePlus size={16} />
          </button>
          {/* Scraper Portal */}
          <button className="new-chat-btn" onClick={() => setShowScraper(!showScraper)} title="Scraper Portal" style={{ marginRight: '8px' }}>
            <Database size={16} />
          </button>
          
          {/* Settings */}
          <button className="new-chat-btn" onClick={() => setSettingsOpen(true)} title="Settings">
            <Settings size={16} />
          </button>
        </div>
      </header>

      {/* Main Content */}
      {showScraper ? (
        <ScraperPortal />
      ) : (
        <>
          <main className="chat-container">
            {messages.length === 0 && (
              <div className="empty-state">
                <div className="empty-icon-wrap">
                  <Sparkles size={40} className="empty-icon" />
                </div>
                <h2>How can I assist you with Indian Standards?</h2>
                <p>Ask about BIS certifications, ISI mark, Hallmarking, CRS, Quality Control Orders, or any BIS guideline.</p>
                <div className="quick-prompts">
                  {[
                    { icon: Award, text: 'Hallmarking process', q: 'What is the hallmarking process for gold jewellery?' },
                    { icon: CheckCircle, text: 'ISI Mark process', q: 'How to get ISI mark for my product?' },
                    { icon: Droplet, text: 'IS 14543 Water', q: 'What is the permissible limit of Lead in Packaged Drinking Water as per IS 14543?' },
                    { icon: Smartphone, text: 'CRS for electronics', q: 'What is CRS scheme for electronics?' },
                  ].map(({ icon: Icon, text, q }, i) => (
                    <button key={i} className="prompt-card" style={{ animationDelay: `${i * 0.08}s` }} onClick={() => handleSend(q)}>
                      <Icon size={18} />
                      <span>{text}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg, index) => (
              <div key={index} className={`message-wrapper ${msg.role}`}>
                <div className="message-block">
                  {msg.role === 'assistant' && (
                    <div className="thought-badge">
                      <span>Thought for {msg.thinkTime || 3}s</span>
                      {msg.confidence && <ConfidenceBadge confidence={msg.confidence} />}
                    </div>
                  )}

                  <div className={`message-bubble ${msg.role}`}>
                    {msg.role === 'assistant' ? (
                      <div className="message-content markdown-body">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                      </div>
                    ) : (
                      <p className="message-content">{msg.content}</p>
                    )}

                    {msg.role === 'assistant' && msg.citations && msg.citations.length > 0 && (
                      <div className="citations">
                        <span className="cit-label"><FileText size={12} /> Sources:</span>
                        {msg.citations.map((cit, i) => {
                          const sourcePath = (cit.source || cit.title || '').replace(/\\/g, '/');
                          return (
                            <a key={i} className="citation-chip" href={`${API_BASE_URL}/source/${encodeURI(sourcePath)}`} target="_blank" rel="noopener noreferrer">
                              <FileText size={10} />
                              <span className="cit-title">{cit.title || sourcePath}</span>
                              <ExternalLink size={10} className="cit-external" />
                            </a>
                          );
                        })}
                      </div>
                    )}
                  </div>

                  {msg.role === 'assistant' && (
                    <div className="action-toolbar">
                      <button onClick={() => copyToClipboard(msg.content, index)} title="Copy">
                        {copiedIndex === index ? <Check size={15} className="text-green" /> : <Copy size={15} />}
                      </button>
                      <button onClick={() => speakText(msg.content, index)} title="Read Aloud">
                        {speakingIndex === index ? <VolumeX size={15} className="text-active" /> : <Volume2 size={15} />}
                      </button>
                      <button onClick={() => handleFeedback(msg.id, true)} title="Good"><ThumbsUp size={15} /></button>
                      <button onClick={() => handleFeedback(msg.id, false)} title="Bad"><ThumbsDown size={15} /></button>
                      <button onClick={() => handleRegenerate(msg.queryContext || messages[index - 1]?.content)} title="Regenerate"><RotateCw size={15} /></button>
                    </div>
                  )}

                  {msg.role === 'user' && (
                    <div className="user-action-toolbar">
                      <button onClick={() => handleRegenerate(msg.content)} title="Retry"><RotateCw size={15} /></button>
                      <button onClick={() => setInput(msg.origText || msg.content)} title="Edit"><Edit3 size={15} /></button>
                      <button onClick={() => copyToClipboard(msg.content, index)} title="Copy">
                        {copiedIndex === index ? <Check size={15} /> : <Copy size={15} />}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="message-wrapper assistant">
                <div className="message-block" style={{ marginLeft: '12px' }}>
                  <LatticeLoader status="working" label="AI Thinking" grid={3} shape="round" cellSize={6} gap={2} fontSize={12} step={90} idleOpacity={0.15} glow showTimer />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </main>

          {/* Input Bar */}
          <footer className="input-area-wrapper">
            <div className="input-bar">
              <textarea
                ref={inputRef}
                className="chat-input"
                rows={1}
                value={input}
                onChange={(e) => {
                  setInput(e.target.value);
                  e.target.style.height = '0';
                  e.target.style.height = Math.min(e.target.scrollHeight, 140) + 'px';
                }}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                placeholder="Ask about BIS standards, hallmarking, ISI mark, CRS..."
              />

              <div className="input-actions">
                <button type="button" className={`input-icon-btn ${isListening ? 'listening' : ''}`} onClick={toggleListening} title="Voice">
                  {isListening ? <MicOff size={18} /> : <Mic size={18} />}
                </button>
                <button
                  type="button"
                  className={`send-btn ${input.trim() ? 'armed' : ''}`}
                  onClick={() => handleSend()}
                  disabled={isLoading || !input.trim()}
                  title="Send"
                >
                  <Send size={16} />
                </button>
              </div>
            </div>
          </footer>
        </>
      )}

      {/* Settings Modal */}
      {settingsOpen && (
        <div className="modal-overlay" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div className="modal-content" style={{ backgroundColor: 'var(--bg-card, #1e1e1e)', padding: '24px', borderRadius: '12px', width: '400px', border: '1px solid var(--border-color, #333)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h2 style={{ margin: 0, fontSize: '18px' }}>Settings</h2>
              <button onClick={() => setSettingsOpen(false)} style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer' }}><X size={20} /></button>
            </div>
            
            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', color: 'var(--text-secondary, #aaa)' }}>Logo URL</label>
              <input 
                type="text" 
                value={tempLogoUrl} 
                onChange={(e) => setTempLogoUrl(e.target.value)} 
                placeholder="https://example.com/logo.png"
                style={{ width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid var(--border-color, #444)', backgroundColor: 'var(--bg-input, #111)', color: '#fff', boxSizing: 'border-box' }}
              />
            </div>
            
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <button onClick={() => setSettingsOpen(false)} style={{ padding: '8px 16px', borderRadius: '6px', border: '1px solid #555', background: 'transparent', color: '#fff', cursor: 'pointer' }}>Cancel</button>
              <button onClick={handleSaveSettings} style={{ padding: '8px 16px', borderRadius: '6px', border: 'none', backgroundColor: 'var(--primary-color, #3b82f6)', color: '#fff', cursor: 'pointer', fontWeight: 'bold' }}>Save Changes</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
