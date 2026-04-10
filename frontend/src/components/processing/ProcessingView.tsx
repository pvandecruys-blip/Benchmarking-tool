import { useEffect, useRef } from 'react';
import { CheckCircle, Loader, Clock, AlertCircle } from 'lucide-react';
import { useStore } from '../../store/useStore';
import { api } from '../../lib/api';
import type { ProcessingStatus } from '../../lib/types';

export default function ProcessingView() {
  const { projectId, processingStatus, setProcessingStatus, setView, setMetrics, setSummary } = useStore();
  const intervalRef = useRef<number | null>(null);
  const logEndRef = useRef<HTMLDivElement>(null);

  // Poll status
  useEffect(() => {
    if (!projectId) return;

    const poll = async () => {
      try {
        const status = await api.getStatus(projectId) as ProcessingStatus;
        setProcessingStatus(status);

        if (status.status === 'complete') {
          // Fetch final results
          const metrics = await api.getMetrics(projectId) as any[];
          setMetrics(metrics);
          if (status.summary) setSummary(status.summary);
          if (intervalRef.current) clearInterval(intervalRef.current);
          setTimeout(() => setView('results'), 1500);
        } else if (status.status === 'error') {
          if (intervalRef.current) clearInterval(intervalRef.current);
        }
      } catch (e) {
        console.error('Poll error:', e);
      }
    };

    poll();
    intervalRef.current = window.setInterval(poll, 2000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [projectId]);

  // Auto-scroll log
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [processingStatus?.log]);

  const status = processingStatus;
  if (!status) return (
    <div className="flex-1 flex items-center justify-center">
      <Loader size={32} className="animate-spin text-[var(--color-electric)]" />
    </div>
  );

  const phases = [
    { name: 'Phase 1: Parse & Extract', key: 'phase1' },
    { name: 'Phase 2: Verify & Match', key: 'phase2' },
    { name: 'Phase 3: Annotate & Report', key: 'phase3' },
  ];

  const currentPhaseIdx = phases.findIndex(p => status.current_phase?.includes(p.key.replace('phase', 'Phase ')));

  const getPhaseIcon = (idx: number) => {
    if (status.status === 'complete') return <CheckCircle size={18} className="text-[var(--color-emerald)]" />;
    if (status.status === 'error') return <AlertCircle size={18} className="text-[var(--color-rose)]" />;
    if (idx < currentPhaseIdx) return <CheckCircle size={18} className="text-[var(--color-emerald)]" />;
    if (idx === currentPhaseIdx) return <Loader size={18} className="animate-spin text-[var(--color-electric)]" />;
    return <Clock size={18} className="text-[var(--color-navy-600)]" />;
  };

  return (
    <div className="flex-1 p-6 animate-fade-in">
      <div className="max-w-3xl mx-auto">
        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold mb-2">
            {status.status === 'complete' ? (
              <span className="text-[var(--color-emerald)]">✅ Analysis Complete</span>
            ) : status.status === 'error' ? (
              <span className="text-[var(--color-rose)]">❌ Analysis Failed</span>
            ) : (
              <span className="gradient-text">Analysing...</span>
            )}
          </h2>
          <p className="text-sm text-[var(--color-navy-400)]">{status.progress_message}</p>
        </div>

        {/* Progress bar */}
        <div className="mb-8">
          <div className="flex justify-between text-xs text-[var(--color-navy-500)] mb-2">
            <span>{status.current_phase}</span>
            <span>{status.progress_pct}%</span>
          </div>
          <div className="progress-bar-track">
            <div className="progress-bar-fill" style={{ width: `${status.progress_pct}%` }} />
          </div>
        </div>

        {/* Phase tracker */}
        <div className="glass-card p-6 mb-6">
          <div className="space-y-4">
            {phases.map((phase, idx) => (
              <div key={phase.key} className="flex items-center gap-3">
                {getPhaseIcon(idx)}
                <span className={`text-sm ${idx <= currentPhaseIdx ? 'text-[var(--color-navy-200)]' : 'text-[var(--color-navy-600)]'}`}>
                  {phase.name}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Live feed */}
        <div className="glass-card p-6">
          <h3 className="text-sm font-semibold text-[var(--color-navy-400)] mb-4 uppercase tracking-wider">
            Live Feed
          </h3>
          <div className="max-h-64 overflow-y-auto space-y-1 font-mono text-xs">
            {status.log.map((entry, i) => (
              <div key={i} className="flex gap-2 py-1 animate-fade-in" style={{ animationDelay: `${i * 0.02}s` }}>
                <span>{entry.emoji}</span>
                <span className="text-[var(--color-navy-400)]">
                  {new Date(entry.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
                <span className="text-[var(--color-navy-300)]">{entry.message}</span>
              </div>
            ))}
            <div ref={logEndRef} />
          </div>
        </div>
      </div>
    </div>
  );
}
