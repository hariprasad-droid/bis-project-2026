import React, { useState } from 'react';

const JellyRadio = ({
  items,
  defaultValue,
  onChange,
  chipColor = 'rgba(255,255,255,0.03)',
  activeColor = '#8b5cf6',
  textColor = '#a1a1aa',
  activeTextColor = '#ffffff',
  size = 'md',
  gap = 4,
  radius = 20,
}) => {
  const [activeIdx, setActiveIdx] = useState(() => {
    return items.findIndex(item => (typeof item === 'string' ? item : item.value) === defaultValue) || 0;
  });

  const handleSelect = (index) => {
    const item = items[index];
    if (typeof item === 'object' && item.disabled) return;
    
    setActiveIdx(index);
    if (onChange) {
      const value = typeof item === 'string' ? item : item.value;
      onChange(value, index);
    }
  };

  const getPadding = () => {
    switch (size) {
      case 'sm': return '6px 14px';
      case 'lg': return '10px 24px';
      case 'md':
      default: return '8px 18px';
    }
  };

  const getFontSize = () => {
    switch (size) {
      case 'sm': return '0.75rem';
      case 'lg': return '1rem';
      case 'md':
      default: return '0.85rem';
    }
  };

  return (
    <div 
      style={{
        display: 'flex',
        alignItems: 'center',
        position: 'relative',
        background: chipColor,
        padding: '4px',
        borderRadius: `${radius + 4}px`,
        border: '1px solid rgba(255,255,255,0.08)',
        boxShadow: 'inset 0 2px 10px rgba(0,0,0,0.2)'
      }}
    >
      {/* Animated Background Slider */}
      <div 
        style={{
          position: 'absolute',
          top: '4px',
          bottom: '4px',
          left: '4px',
          width: `calc((100% - 8px) / ${items.length})`,
          transform: `translateX(calc(100% * ${activeIdx}))`,
          backgroundColor: activeColor,
          borderRadius: `${radius}px`,
          transition: 'transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)',
          boxShadow: '0 2px 10px rgba(139, 92, 246, 0.4)'
        }}
      />

      {items.map((item, i) => {
        const isString = typeof item === 'string';
        const label = isString ? item : item.label;
        const icon = isString ? null : item.icon;
        const disabled = isString ? false : item.disabled;
        const isActive = activeIdx === i;

        return (
          <button
            key={isString ? item : item.value}
            onClick={() => handleSelect(i)}
            disabled={disabled}
            style={{
              position: 'relative',
              zIndex: 1,
              flex: 1,
              background: 'transparent',
              border: 'none',
              padding: getPadding(),
              fontSize: getFontSize(),
              fontWeight: isActive ? 600 : 500,
              color: isActive ? activeTextColor : textColor,
              cursor: disabled ? 'not-allowed' : 'pointer',
              opacity: disabled ? 0.4 : 1,
              borderRadius: `${radius}px`,
              transition: 'color 0.3s ease',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              fontFamily: 'inherit',
              whiteSpace: 'nowrap'
            }}
          >
            {icon && <span>{icon}</span>}
            {label}
          </button>
        );
      })}
    </div>
  );
};

export default JellyRadio;
