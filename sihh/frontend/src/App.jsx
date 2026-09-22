import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, ThumbsUp, ThumbsDown, Mic, MicOff, Volume2, VolumeX, 
  Copy, Check, RotateCw, Plus, Paperclip, Sparkles, Edit3,
  FileText, ExternalLink, MessageSquarePlus, Shield, ShieldCheck, ShieldAlert, Settings, X
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ScraperPortal from './ScraperPortal';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [language, setLanguage] = useState('en');
  const [sessionId, setSessionId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [speakingIndex, setSpeakingIndex] = useState(null);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [attachedFile, setAttachedFile] = useState(null);
  const [loadingStartTime, setLoadingStartTime] = useState(null);
  const [thinkingSeconds, setThinkingSeconds] = useState(0);
  const [activeTab, setActiveTab] = useState('chat');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [apiSettings, setApiSettings] = useState(() => {
    const saved = localStorage.getItem('bisApiSettings');
    return saved ? JSON.parse(saved) : { url: '', key: '', model: '' };
  });

  const saveApiSettings = (settings) => {
    setApiSettings(settings);
    localStorage.setItem('bisApiSettings', JSON.stringify(settings));
    setIsSettingsOpen(false);
  };

  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const recognitionRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Live thinking timer
  useEffect(() => {
    let interval;
    if (isLoading && loadingStartTime) {
      interval = setInterval(() => {
        setThinkingSeconds(Math.floor((Date.now() - loadingStartTime) / 1000));
      }, 100);
    } else {
      setThinkingSeconds(0);
    }
    return () => clearInterval(interval);
  }, [isLoading, loadingStartTime]);

  // Setup Web Speech API (Speech Recognition)
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = language === 'hi' ? 'hi-IN' : 'en-US';

      recognition.onresult = (event) => {
        const transcript = Array.from(event.results)
          .map(result => result[0].transcript)
          .join('');
        setInput(transcript);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognition.onerror = (err) => {
        console.error("Speech recognition error:", err);
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    }
  }, [language]);

  const toggleListening = () => {
    if (!recognitionRef.current) {
      alert("Speech recognition is not supported in this browser.");
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      recognitionRef.current.start();
      setIsListening(true);
    }
  };

  // Text to Speech
  const speakText = (text, index) => {
    if (!('speechSynthesis' in window)) {
      alert("Text-to-speech is not supported in this browser.");
      return;
    }

    if (speakingIndex === index) {
      window.speechSynthesis.cancel();
      setSpeakingIndex(null);
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = language === 'hi' ? 'hi-IN' : 'en-US';

    utterance.onend = () => setSpeakingIndex(null);
    utterance.onerror = () => setSpeakingIndex(null);

    setSpeakingIndex(index);
    window.speechSynthesis.speak(utterance);
  };

  // Copy to clipboard
  const copyToClipboard = (text, index) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  // Handle File Selection
  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setAttachedFile(e.target.files[0]);
    }
  };

  // New Chat
  const handleNewChat = () => {
    setMessages([]);
    setSessionId(null);
    setInput('');
    setAttachedFile(null);
    window.speechSynthesis?.cancel();
    setSpeakingIndex(null);
  };

  const handleSend = async (customMessage = null) => {
    const textToSend = customMessage || input;
    if (!textToSend.trim() && !attachedFile) return;

    let displayContent = textToSend;
    if (attachedFile) {
      displayContent = `[Attached: ${attachedFile.name}]\n${textToSend}`;
    }

    const userMessage = { role: 'user', content: displayContent, origText: textToSend };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setAttachedFile(null);
    setIsLoading(true);
    setLoadingStartTime(Date.now());

    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: textToSend,
          language,
          session_id: sessionId,
          custom_api_url: apiSettings.url || undefined,
          custom_api_key: apiSettings.key || undefined,
          custom_model: apiSettings.model || undefined
        }),
      });

      const data = await response.json();

      if (!sessionId) {
        setSessionId(data.session_id);
      }

      const elapsed = Math.max(1, Math.floor((Date.now() - (loadingStartTime || Date.now())) / 1000));

      setMessages((prev) => [
        ...prev,
        {
          id: data.message_id,
          role: 'assistant',
          content: data.answer,
          citations: data.citations,
          confidence: data.confidence,
          queryContext: textToSend,
          thinkTime: elapsed,
        }
      ]);
    } catch (error) {
      console.error('Error fetching chat response:', error);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'An error occurred while connecting to the server. Please check that the backend is running.' }
      ]);
    } finally {
      setIsLoading(false);
      setLoadingStartTime(null);
    }
  };

  // Regenerate Response
  const handleRegenerate = async (lastUserText) => {
    if (!lastUserText || isLoading) return;
    setIsLoading(true);
    setLoadingStartTime(Date.now());
    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: lastUserText,
          language,
          session_id: sessionId,
          custom_api_url: apiSettings.url || undefined,
          custom_api_key: apiSettings.key || undefined,
          custom_model: apiSettings.model || undefined
        }),
      });
      const data = await response.json();
      const elapsed = Math.max(1, Math.floor((Date.now() - (loadingStartTime || Date.now())) / 1000));
      setMessages((prev) => [
        ...prev,
        {
          id: data.message_id,
          role: 'assistant',
          content: data.answer,
          citations: data.citations,
          confidence: data.confidence,
          queryContext: lastUserText,
          thinkTime: elapsed,
        }
      ]);
    } catch (error) {
      console.error('Error regenerating:', error);
    } finally {
      setIsLoading(false);
      setLoadingStartTime(null);
    }
  };

  const handleFeedback = async (messageId, isPositive) => {
    try {
      await fetch(`${API_BASE_URL}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message_id: messageId,
          is_positive: isPositive
        }),
      });
    } catch (error) {
      console.error('Error submitting feedback:', error);
    }
  };

  // Confidence badge component
  const ConfidenceBadge = ({ confidence }) => {
    if (!confidence) return null;
    const config = {
      high: { icon: ShieldCheck, label: 'High confidence', className: 'confidence-high' },
      medium: { icon: Shield, label: 'Medium confidence', className: 'confidence-medium' },
      low: { icon: ShieldAlert, label: 'Low confidence', className: 'confidence-low' },
    };
    const c = config[confidence] || config.medium;
    const Icon = c.icon;
    return (
      <span className={`confidence-badge ${c.className}`} title={c.label}>
        <Icon size={12} />
        {c.label}
      </span>
    );
  };

  // File type icon helper
  const getFileIcon = (fileType) => {
    if (fileType === 'pdf') return '📄';
    if (fileType === 'html' || fileType === 'htm') return '🌐';
    if (fileType === 'txt') return '📝';
    return '📎';
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="logo-section">
          <Sparkles className="sparkle-icon" size={20} />
          <h1>BIS Standards Assistant</h1>
        </div>
        <div className="header-controls">
          <div className="tab-switcher">
            <button className={`tab-btn ${activeTab === 'chat' ? 'active' : ''}`} onClick={() => setActiveTab('chat')}>Chat</button>
            <button className={`tab-btn ${activeTab === 'scraper' ? 'active' : ''}`} onClick={() => setActiveTab('scraper')}>Scraper Portal</button>
          </div>
          <button className="new-chat-btn" onClick={handleNewChat} title="New Chat">
            <MessageSquarePlus size={18} />
            <span>New Chat</span>
          </button>
          <div className="language-selector">
            <select 
              id="lang" 
              value={language} 
              onChange={(e) => setLanguage(e.target.value)}
            >
              <option value="en">English</option>
              <option value="hi">Hindi</option>
              <option value="ta">Tamil</option>
              <option value="te">Telugu</option>
              <option value="bn">Bengali</option>
            </select>
          </div>
          <button className="icon-btn" onClick={() => setIsSettingsOpen(true)} title="Settings">
            <Settings size={20} />
          </button>
        </div>
      </header>

      {/* Main Chat Stream */}
      {activeTab === 'chat' ? (
      <React.Fragment>
      <main className="chat-container">
        {messages.length === 0 && (
          <div className="empty-state">
            <Sparkles size={48} className="empty-icon" />
            <h2>How can I assist you with Indian Standards today?</h2>
            <p>Ask about BIS certifications, ISI mark schemes, Hallmarking, product compliance, Quality Control Orders, or any BIS guideline.</p>
            <div className="quick-prompts">
              <button onClick={() => handleSend("What is the hallmarking process for gold jewellery?")}>
                🏅 Hallmarking process
              </button>
              <button onClick={() => handleSend("How to get ISI mark for my product?")}>
                ✅ ISI Mark process
              </button>
              <button onClick={() => handleSend("What is the permissible limit of Lead in Packaged Drinking Water as per IS 14543?")}>
                💧 IS 14543 Drinking Water
              </button>
              <button onClick={() => handleSend("What is CRS scheme for electronics?")}>
                📱 CRS for electronics
              </button>
            </div>
          </div>
        )}

        {messages.map((msg, index) => (
          <div key={index} className={`message-wrapper ${msg.role}`}>
            <div className="message-block">
              {/* Thought badge for assistant */}
              {msg.role === 'assistant' && (
                <div className="thought-badge">
                  <span>Thought for {msg.thinkTime || 3}s</span>
                  {msg.confidence && <ConfidenceBadge confidence={msg.confidence} />}
                </div>
              )}

              <div className={`message-bubble ${msg.role}`}>
                {msg.role === 'assistant' ? (
                  <div className="message-content markdown-body">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <p className="message-content">{msg.content}</p>
                )}

                {/* Citations section */}
                {msg.role === 'assistant' && msg.citations && msg.citations.length > 0 && (
                  <div className="citations">
                    <span className="cit-label">
                      <FileText size={12} />
                      Sources:
                    </span>
                    {msg.citations.map((cit, i) => {
                      const sourcePath = (cit.source || cit.title || '').replace(/\\/g, '/');
                      const fileUrl = `${API_BASE_URL}/source/${encodeURI(sourcePath)}`;
                      const fileIcon = getFileIcon(cit.file_type);
                      return (
                        <a
                          key={i}
                          className="citation-chip"
                          title={`Click to open: ${cit.title || sourcePath}`}
                          href={fileUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <span className="cit-icon">{fileIcon}</span>
                          <span className="cit-title">{cit.title || sourcePath}</span>
                          <ExternalLink size={10} className="cit-external" />
                        </a>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Action Toolbar */}
              {msg.role === 'assistant' && (
                <div className="action-toolbar">
                  <button onClick={() => copyToClipboard(msg.content, index)} title="Copy">
                    {copiedIndex === index ? <Check size={16} className="text-green" /> : <Copy size={16} />}
                  </button>
                  <button onClick={() => speakText(msg.content, index)} title="Read Aloud">
                    {speakingIndex === index ? <VolumeX size={16} className="text-active" /> : <Volume2 size={16} />}
                  </button>
                  <button onClick={() => handleFeedback(msg.id, true)} title="Good response">
                    <ThumbsUp size={16} />
                  </button>
                  <button onClick={() => handleFeedback(msg.id, false)} title="Bad response">
                    <ThumbsDown size={16} />
                  </button>
                  <button onClick={() => handleRegenerate(msg.queryContext || messages[index-1]?.content)} title="Regenerate">
                    <RotateCw size={16} />
                  </button>
                </div>
              )}

              {msg.role === 'user' && (
                <div className="user-action-toolbar">
                  <button onClick={() => handleRegenerate(msg.content)} title="Retry">
                    <RotateCw size={16} />
                  </button>
                  <button onClick={() => setInput(msg.origText || msg.content)} title="Edit prompt">
                    <Edit3 size={16} />
                  </button>
                  <button onClick={() => copyToClipboard(msg.content, index)} title="Copy">
                    {copiedIndex === index ? <Check size={16} /> : <Copy size={16} />}
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="message-wrapper assistant">
            <div className="message-block">
              <div className="thought-badge pulsing">
                <span>Thinking for {thinkingSeconds}s...</span>
              </div>
              <div className="message-bubble assistant loading">
                <div className="loading-dots">
                  <span></span><span></span><span></span>
                </div>
                Searching knowledge base...
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </main>

      {/* Input Bar */}
      <footer className="input-area-wrapper">
        {attachedFile && (
          <div className="attached-file-tag">
            <Paperclip size={14} />
            <span>{attachedFile.name}</span>
            <button onClick={() => setAttachedFile(null)}>×</button>
          </div>
        )}
        <div className="input-bar">
          <input 
            type="file" 
            ref={fileInputRef} 
            style={{ display: 'none' }} 
            onChange={handleFileChange}
          />
          <button 
            type="button"
            className="icon-btn attach-btn" 
            onClick={() => fileInputRef.current?.click()}
            title="Attach file"
          >
            <Plus size={20} />
          </button>

          <input
            type="text"
            className="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask about BIS standards, hallmarking, ISI mark, CRS..."
          />

          <div className="input-controls-right">
            <button 
              type="button"
              className={`icon-btn mic-btn ${isListening ? 'listening' : ''}`}
              onClick={toggleListening}
              title={isListening ? "Stop Listening" : "Voice Input"}
            >
              {isListening ? <MicOff size={18} /> : <Mic size={18} />}
            </button>

            <button 
              type="button"
              className="icon-btn send-btn"
              onClick={() => handleSend()}
              disabled={isLoading || (!input.trim() && !attachedFile)}
              title="Send"
            >
              <div className="waveform-icon">
                <Send size={18} />
              </div>
            </button>
          </div>
        </div>
      </footer>
      </React.Fragment>
      ) : (
        <ScraperPortal />
      )}

      {/* Settings Modal */}
      {isSettingsOpen && (
        <div className="modal-overlay" style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex',
          alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}>
          <div className="modal-content" style={{
            backgroundColor: 'var(--bg-card, #ffffff)', padding: '24px',
            borderRadius: '12px', width: '90%', maxWidth: '400px',
            boxShadow: '0 10px 25px rgba(0,0,0,0.1)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h2 style={{ margin: 0, fontSize: '1.25rem' }}>API Settings</h2>
              <button onClick={() => setIsSettingsOpen(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }}>
                <X size={20} />
              </button>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.9rem', fontWeight: 500 }}>Custom API URL</label>
                <input 
                  type="text" 
                  value={apiSettings.url} 
                  onChange={e => setApiSettings({...apiSettings, url: e.target.value})}
                  placeholder="https://api.openai.com/v1/chat/completions"
                  style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #ccc', boxSizing: 'border-box' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.9rem', fontWeight: 500 }}>API Key</label>
                <input 
                  type="password" 
                  value={apiSettings.key} 
                  onChange={e => setApiSettings({...apiSettings, key: e.target.value})}
                  placeholder="sk-..."
                  style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #ccc', boxSizing: 'border-box' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.9rem', fontWeight: 500 }}>Model Name</label>
                <input 
                  type="text" 
                  value={apiSettings.model} 
                  onChange={e => setApiSettings({...apiSettings, model: e.target.value})}
                  placeholder="gpt-3.5-turbo"
                  style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #ccc', boxSizing: 'border-box' }}
                />
              </div>
              <button 
                onClick={() => saveApiSettings(apiSettings)}
                style={{
                  background: 'var(--primary-color, #2563eb)', color: 'white', border: 'none',
                  padding: '10px', borderRadius: '6px', cursor: 'pointer', fontWeight: 600, marginTop: '8px'
                }}
              >
                Save Settings
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
