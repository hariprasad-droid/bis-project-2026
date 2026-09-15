import React, { useState, useEffect, useRef } from 'react';
import { Play, Square, Terminal, Database, FileText, ExternalLink, RefreshCw } from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

function ScraperPortal() {
  const [isRunning, setIsRunning] = useState(false);
  const [logs, setLogs] = useState([]);
  const [manifest, setManifest] = useState([]);
  const [loadingAction, setLoadingAction] = useState(false);
  
  const terminalEndRef = useRef(null);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/scraper/status`);
      const data = await res.json();
      setIsRunning(data.is_running);
      setLogs(data.logs);
    } catch (e) {
      console.error("Error fetching scraper status:", e);
    }
  };

  const fetchManifest = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/scraper/manifest`);
      const data = await res.json();
      if (Array.isArray(data)) {
        setManifest(data);
      }
    } catch (e) {
      console.error("Error fetching manifest:", e);
    }
  };

  useEffect(() => {
    fetchStatus();
    fetchManifest();
    const interval = setInterval(() => {
      fetchStatus();
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  const handleStart = async () => {
    setLoadingAction(true);
    try {
      await fetch(`${API_BASE_URL}/scraper/start`, { method: 'POST' });
      await fetchStatus();
    } catch (e) {
      console.error("Error starting scraper:", e);
    } finally {
      setLoadingAction(false);
    }
  };

  const handleStop = async () => {
    setLoadingAction(true);
    try {
      await fetch(`${API_BASE_URL}/scraper/stop`, { method: 'POST' });
      await fetchStatus();
    } catch (e) {
      console.error("Error stopping scraper:", e);
    } finally {
      setLoadingAction(false);
    }
  };

  return (
    <div className="scraper-portal">
      <div className="scraper-header">
        <div className="scraper-title">
          <Database className="text-primary" size={24} />
          <h2>BIS Knowledge Scraper</h2>
        </div>
        
        <div className="scraper-controls">
          <div className={`status-badge ${isRunning ? 'running' : 'stopped'}`}>
            <span className="pulse-dot"></span>
            {isRunning ? 'Crawler Active' : 'Crawler Stopped'}
          </div>
          
          <button 
            className="btn btn-primary" 
            onClick={handleStart} 
            disabled={isRunning || loadingAction}
          >
            <Play size={16} /> Start Crawl
          </button>
          
          <button 
            className="btn btn-danger" 
            onClick={handleStop} 
            disabled={!isRunning || loadingAction}
          >
            <Square size={16} /> Stop Crawl
          </button>
          
          <button 
            className="btn btn-secondary icon-only" 
            onClick={fetchManifest}
            title="Refresh Data"
          >
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      <div className="scraper-grid">
        <div className="scraper-terminal-container">
          <div className="panel-header">
            <Terminal size={16} />
            <h3>Live Process Logs</h3>
          </div>
          <div className="terminal-window">
            {logs.length === 0 ? (
              <div className="text-muted">No logs available...</div>
            ) : (
              logs.map((log, i) => (
                <div key={i} className="log-line">{log}</div>
              ))
            )}
            <div ref={terminalEndRef} />
          </div>
        </div>

        <div className="scraper-data-container">
          <div className="panel-header">
            <FileText size={16} />
            <h3>Scraped Documents ({manifest.length})</h3>
          </div>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Source URL</th>
                  <th>Fetched At</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {manifest.length === 0 ? (
                  <tr>
                    <td colSpan="4" className="text-center text-muted">No documents scraped yet.</td>
                  </tr>
                ) : (
                  manifest.map((item, idx) => {
                    // Make a safe path to pass to /source/
                    const sourcePath = (item.local_path || item.url).replace(/\\/g, '/').split('/raw/').pop() || '';
                    const fileUrl = `${API_BASE_URL}/source/${encodeURI(sourcePath)}`;
                    const date = item.fetched_at ? new Date(item.fetched_at).toLocaleString() : 'Unknown';
                    
                    return (
                      <tr key={idx}>
                        <td>
                          <span className={`file-type-badge ${item.is_pdf ? 'pdf' : 'html'}`}>
                            {item.is_pdf ? 'PDF' : 'HTML'}
                          </span>
                        </td>
                        <td className="url-cell" title={item.url}>{item.url}</td>
                        <td className="date-cell">{date}</td>
                        <td>
                          <a 
                            href={fileUrl} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="btn-view"
                          >
                            View <ExternalLink size={12} />
                          </a>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ScraperPortal;
