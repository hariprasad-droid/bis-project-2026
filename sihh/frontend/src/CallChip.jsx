import React, { useState, useEffect } from 'react';
import { Terminal, Database, Cpu, Sparkles, AlertCircle, CheckCircle2 } from 'lucide-react';

const CallChip = ({
  icon,
  name,
  argument,
  status = 'running', // 'running', 'done', 'error'
  expectedMs = 3000,
  size = 34,
  radius = 10,
  color = '#e4e4e7',
  surfaceColor = '#27272a',
  progressColor = '#8b5cf6',
  progressOpacity = 0.15,
  doneColor = '#22c55e',
  errorColor = '#ef4444',
  washOpacity = 0.14,
  shake = 6,
  showTimer = true,
  onRetry
}) => {
  const [elapsed, setElapsed] = useState(0);
  
  useEffect(() => {
    let interval;
    if (status === 'running') {
      interval = setInterval(() => {
        setElapsed(prev => prev + 100);
      }, 100);
    }
    return () => clearInterval(interval);
  }, [status]);

  // Calculate progress percentage
  const progress = Math.min((elapsed / expectedMs) * 100, 100);
  
  const getIcon = () => {
    if (status === 'done') return <CheckCircle2 size={16} color={doneColor} />;
    if (status === 'error') return <AlertCircle size={16} color={errorColor} />;
    switch(icon) {
      case 'terminal': return <Terminal size={16} />;
      case 'database': return <Database size={16} />;
      case 'cpu': return <Cpu size={16} />;
      default: return <Sparkles size={16} className="pulsing-icon" />;
    }
  };

  const getBorderColor = () => {
    if (status === 'done') return doneColor;
    if (status === 'error') return errorColor;
    return 'rgba(255, 255, 255, 0.1)';
  };

  const formatTime = (ms) => {
    return (ms / 1000).toFixed(1) + 's';
  };

  return (
    <div 
      className={`call-chip-container ${status === 'error' ? 'shake-animation' : ''}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        background: surfaceColor,
        borderRadius: `${radius}px`,
        padding: '6px 12px',
        color: color,
        border: `1px solid ${getBorderColor()}`,
        position: 'relative',
        overflow: 'hidden',
        boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
        gap: '10px',
        fontFamily: 'inherit',
        minWidth: '220px',
        transition: 'all 0.3s ease'
      }}
    >
      {/* Background Progress Fill */}
      {status === 'running' && (
        <div style={{
          position: 'absolute',
          left: 0,
          top: 0,
          height: '100%',
          width: `${progress}%`,
          backgroundColor: progressColor,
          opacity: progressOpacity,
          transition: 'width 0.1s linear',
          zIndex: 0
        }} />
      )}

      {/* Content */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', zIndex: 1, flex: 1 }}>
        <div style={{ opacity: status === 'running' ? 0.8 : 1, transition: 'opacity 0.3s' }}>
          {getIcon()}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 600, letterSpacing: '0.02em', color: status === 'error' ? errorColor : status === 'done' ? doneColor : color }}>
            {name}
          </span>
          <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.5)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '140px' }}>
            {argument}
          </span>
        </div>
      </div>

      {/* Timer / Retry */}
      <div style={{ zIndex: 1, fontSize: '0.7rem', fontWeight: 500, color: 'rgba(255,255,255,0.6)', marginLeft: 'auto' }}>
        {status === 'running' && showTimer && formatTime(elapsed)}
        {status === 'done' && showTimer && formatTime(elapsed)}
        {status === 'error' && onRetry && (
          <button 
            onClick={onRetry}
            style={{
              background: 'none', border: 'none', color: errorColor, 
              cursor: 'pointer', fontSize: '0.7rem', fontWeight: 'bold'
            }}
          >
            RETRY
          </button>
        )}
      </div>

      <style>{`
        .pulsing-icon { animation: chipPulse 1.5s infinite; }
        @keyframes chipPulse { 0%, 100% { opacity: 0.5; } 50% { opacity: 1; transform: scale(1.1); } }
        .shake-animation { animation: shakeX 0.4s; }
        @keyframes shakeX {
          0%, 100% { transform: translateX(0); }
          25% { transform: translateX(-${shake}px); }
          75% { transform: translateX(${shake}px); }
        }
      `}</style>
    </div>
  );
};

export default CallChip;
