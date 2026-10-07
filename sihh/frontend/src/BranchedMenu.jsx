import { useLayoutEffect, useMemo, useRef, useState, useId } from 'react';
import { HugeiconsIcon } from '@hugeicons/react';
import { ArrowRight01Icon } from '@hugeicons/core-free-icons';
import './BranchedMenu.css';

export default function BranchedMenu({
  items,
  defaultOpen = [],
  defaultActive = '',
  onSelect,
  color = '#f5f5f5',
  accentColor = '#f5f5f5',
  lineColor = '#3f3f46',
  width = 240,
  rowHeight = 36,
  indent = 40,
  trunk = 14,
  radius = 10,
  lineWidth = 1.5,
  fontSize = 14,
  drawDuration = 400,
  foldDuration = 300,
  className = ''
}) {
  const [open, setOpen] = useState(new Set(defaultOpen));
  const [active, setActive] = useState(defaultActive);
  const [prevOpen, setPrevOpen] = useState(new Set(defaultOpen));
  const id = useId();
  const rootRef = useRef(null);

  const flat = useMemo(() => {
    const list = [];
    items.forEach((group, gi) => {
      list.push({ type: 'group', id: `g${gi}`, label: group.label, open: open.has(gi), i: gi });
      if (open.has(gi)) {
        group.children.forEach((item, ii) => {
          list.push({ type: 'item', id: `i${gi}-${ii}`, item, gi, ii });
        });
      }
    });
    return list;
  }, [items, open]);

  const drawLines = useMemo(() => {
    const lines = [];
    items.forEach((group, gi) => {
      const isWasOpen = open.has(gi) || prevOpen.has(gi);
      if (!isWasOpen) return;

      const groupIdx = flat.findIndex(f => f.type === 'group' && f.i === gi);
      let count = 0;
      if (open.has(gi)) {
        count = group.children.length;
      } else {
        count = group.children.length;
      }

      if (count > 0) {
        lines.push({
          id: `l${gi}`,
          start: groupIdx,
          count: count,
          open: open.has(gi),
          wasOpen: prevOpen.has(gi)
        });
      }
    });
    return lines;
  }, [items, open, prevOpen, flat]);

  const toggle = gi => {
    setPrevOpen(new Set(open));
    setOpen(prev => {
      const next = new Set(prev);
      if (next.has(gi)) next.delete(gi);
      else next.add(gi);
      return next;
    });
  };

  const pick = item => {
    if (item.value) setActive(item.value);
    onSelect?.(item.value, item);
  };

  useLayoutEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    const paths = root.querySelectorAll('.branched-menu__path');
    paths.forEach(p => {
      if (p instanceof SVGPathElement) {
        const len = p.getTotalLength();
        p.style.setProperty('--bm-len', `${len}px`);
      }
    });
  }, [flat]);

  const half = rowHeight / 2;
  return (
    <div
      ref={rootRef}
      className={`branched-menu${className ? ` ${className}` : ''}`}
      style={{
        '--bm-color': color,
        '--bm-accent': accentColor,
        '--bm-line': lineColor,
        '--bm-w': `${width}px`,
        '--bm-row': `${rowHeight}px`,
        '--bm-indent': `${indent}px`,
        '--bm-trunk': `${trunk}px`,
        '--bm-radius': `${radius}px`,
        '--bm-line-w': `${lineWidth}px`,
        '--bm-font': `${fontSize}px`,
        '--bm-draw': `${drawDuration}ms`,
        '--bm-fold': `${foldDuration}ms`
      }}
    >
      <div className="branched-menu__list" role="tree">
        {flat.map(f => {
          if (f.type === 'group') {
            return (
              <button
                key={f.id}
                type="button"
                role="treeitem"
                aria-expanded={f.open}
                className="branched-menu__group"
                onClick={() => toggle(f.i)}
              >
                <span>{f.label}</span>
                <span className="branched-menu__chevron" data-open={f.open ? '' : undefined}>
                  <HugeiconsIcon icon={ArrowRight01Icon} size={14} />
                </span>
              </button>
            );
          }
          const isAct = f.item.value === active;
          const Icon = f.item.icon;
          return (
            <button
              key={f.id}
              type="button"
              role="treeitem"
              aria-selected={isAct}
              className="branched-menu__item"
              data-active={isAct ? '' : undefined}
              onClick={() => pick(f.item)}
            >
              {Icon && (
                <span className="branched-menu__icon">
                  {typeof Icon === 'function' ? <Icon size={16} /> : Icon}
                </span>
              )}
              <span className="branched-menu__label">{f.item.label}</span>
            </button>
          );
        })}
      </div>
      <svg className="branched-menu__svg" aria-hidden="true">
        {drawLines.map(l => {
          const sy = l.start * rowHeight + rowHeight;
          const h = l.count * rowHeight;
          return (
            <g key={l.id} transform={`translate(${trunk}, ${sy})`}>
              {Array.from({ length: l.count }).map((_, i) => {
                const ey = i * rowHeight + half;
                const d = `M0,0 L0,${ey - radius} A${radius},${radius} 0 0,0 ${radius},${ey} L${indent - trunk},${ey}`;
                return (
                  <path
                    key={i}
                    d={d}
                    className="branched-menu__path"
                    data-state={l.open ? 'open' : 'closed'}
                  />
                );
              })}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
