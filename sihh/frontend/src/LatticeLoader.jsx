import React, { useState, useEffect } from 'react';
import { CheckCircle2, AlertCircle } from 'lucide-react';

const LatticeLoader = ({
  status = 'working',
  label = 'Thinking',
  doneLabel = 'Done in',
  errorLabel = 'Failed after',
  pattern = 'orbit',
  grid = 3,
  shape = 'round',
  doneColor = '#22c55e',
  errorColor = '#ef4444',
  cellSize = 6,
  gap = 2,
  fontSize = 14,
  step = 90,
  idleOpacity = 0.15,
  glow = false,
  showTimer = true
}) => {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    let interval;
    if (status === 'working') {
      interval = setInterval(() => {
        setElapsed(prev => prev + 100);
      }, 100);
    }
    return () => clearInterval(interval);
  }, [status]);

  const formatTime = (ms) => {
    return (ms / 1000).toFixed(1) + 's';
  };

  const getStatusText = () => {
    if (status === 'done') return `${doneLabel} ${formatTime(elapsed)}`;
    if (status === 'error') return `${errorLabel} ${formatTime(elapsed)}`;
    return showTimer ? `${label} ${formatTime(elapsed)}` : label;
  };

  const getStatusColor = () => {
    if (status === 'done') return doneColor;
    if (status === 'error') return errorColor;
    return '#a1a1aa';
  };

  // Generate 3x3 grid cells for orbit pattern
  const renderGrid = () => {
    if (status === 'done') return <CheckCircle2 size={grid * cellSize + gap * (grid - 1)} color={doneColor} />;
    if (status === 'error') return <AlertCircle size={grid * cellSize + gap * (grid - 1)} color={errorColor} />;

    const cells = [];
    // Orbit pattern indices mapping for 3x3 (outer ring animation)
    const orbitDelays = [
      0, 1, 2,
      7, -1, 3,
      6, 5, 4
    ];

    for (let i = 0; i < grid * grid; i++) {
      const isCenter = i === 4;
      const delay = orbitDelays[i];
      
      cells.push(
        <div
          key={i}
          className={`lattice-cell ${isCenter ? 'center' : 'orbit'}`}
          style={{
            width: `${cellSize}px`,
            height: `${cellSize}px`,
            borderRadius: shape === 'round' ? '50%' : '2px',
            backgroundColor: '#8b5cf6',
            opacity: idleOpacity,
            animation: status === 'working' && !isCenter 
              ? `latticeOrbit ${step * 8}ms infinite linear` 
              : 'none',
            animationDelay: `${delay * step}ms`,
            boxShadow: glow ? `0 0 4px #8b5cf6` : 'none'
          }}
        />
      );
    }

    return (
      <div 
        style={{
          display: 'grid',
          gridTemplateColumns: `repeat(${grid}, ${cellSize}px)`,
          gap: `${gap}px`,
          alignItems: 'center',
          justifyContent: 'center'
        }}
      >
        {cells}
      </div>
    );
  };

  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '10px',
      color: getStatusColor(),
      fontSize: `${fontSize}px`,
      fontWeight: 500,
      fontFamily: 'inherit',
      background: 'rgba(255,255,255,0.03)',
      padding: '4px 12px',
      borderRadius: '20px',
      border: '1px solid rgba(255,255,255,0.05)',
      boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
    }}>
      {renderGrid()}
      <span>{getStatusText()}</span>

      <style>{`
        @keyframes latticeOrbit {
          0%, 100% { opacity: ${idleOpacity}; transform: scale(1); }
          50% { opacity: 1; transform: scale(1.3); background-color: #a78bfa; }
        }
      `}</style>
    </div>
  );
};

export default LatticeLoader;
