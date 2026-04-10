import { Settings, Moon, Sun, RotateCcw } from 'lucide-react';
import { useStore } from '../../store/useStore';
import { useState } from 'react';

export default function Header() {
  const { projectName, view, setShowSettings, reset } = useStore();
  const [dark, setDark] = useState(true);

  return (
    <header className="glass sticky top-0 z-50 px-6 py-3 flex items-center justify-between">
      <div className="flex items-center gap-4">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center"
               style={{ background: 'linear-gradient(135deg, #3b82f6, #10b981)' }}>
            <span className="text-white font-bold text-sm">SL</span>
          </div>
          <h1 className="text-lg font-bold tracking-tight">
            <span className="gradient-text">SourceLens</span>
          </h1>
        </div>

        {/* Project name */}
        {view !== 'upload' && (
          <div className="flex items-center gap-2 ml-4 pl-4 border-l border-white/10">
            <span className="text-sm text-[var(--color-navy-400)]">{projectName}</span>
          </div>
        )}
      </div>

      <div className="flex items-center gap-2">
        {view === 'results' && (
          <button onClick={reset} className="btn-secondary text-xs py-2 px-3" title="New Analysis">
            <RotateCcw size={14} />
            New
          </button>
        )}
        <button
          onClick={() => setShowSettings(true)}
          className="p-2 rounded-lg hover:bg-white/5 transition-colors"
          title="Settings"
        >
          <Settings size={18} className="text-[var(--color-navy-400)]" />
        </button>
        <button
          onClick={() => setDark(!dark)}
          className="p-2 rounded-lg hover:bg-white/5 transition-colors"
          title="Toggle theme"
        >
          {dark ? <Sun size={18} className="text-[var(--color-navy-400)]" /> : <Moon size={18} />}
        </button>
      </div>
    </header>
  );
}
