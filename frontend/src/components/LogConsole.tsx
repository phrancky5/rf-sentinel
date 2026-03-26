import { useState, useEffect, useRef } from 'react';
import { useApp } from '../AppContext';

const statusDot = 'w-2 h-2 rounded-full';
const logRow = 'text-gray-300';
const headerBtn = 'text-xs text-gray-500 hover:text-gray-300 transition-colors';

export default function LogConsole() {
  const { logs, connected, clearLogs: onClear } = useApp();
  const [collapsed, setCollapsed] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!collapsed) bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs, collapsed]);

  return (
    <div className="flex flex-col flex-shrink-0" style={{ height: collapsed ? 33 : 192 }}>
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-700/50">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-gray-400 uppercase tracking-wider">Console</span>
          <span className={`${statusDot} ${connected ? 'bg-green-400' : 'bg-red-400'}`} />
        </div>
        <div className="flex items-center gap-3">
          <button onClick={onClear} className={headerBtn}>Clear</button>
          <button onClick={() => setCollapsed(c => !c)} className="text-sm text-cyan-400 hover:text-cyan-300 transition-colors">
            {collapsed ? '▲' : '▼'}
          </button>
        </div>
      </div>
      {!collapsed && (
        <div className="flex-1 overflow-y-auto p-3 font-mono text-xs leading-relaxed space-y-0.5">
          {logs.length === 0 && (
            <span className="text-gray-600 italic">Waiting for activity...</span>
          )}
          {logs.map((log, i) => (
            <div
              key={i}
              className={`${logRow}${i === logs.length - 1 ? ' log-new' : ''}`}
            >
              <span className="text-gray-600 mr-2">
                {new Date(log.timestamp).toLocaleTimeString('en-GB')}
              </span>
              {log.job_id && (
                <span className="text-cyan-500/60 mr-1">[{log.job_id.slice(0, 6)}]</span>
              )}
              <span className={log.message.includes('ERROR') ? 'text-red-400' : ''}>
                {log.message}
              </span>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
}
