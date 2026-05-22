import { useState, useMemo } from 'react';
import { Download, ChevronRight, X } from 'lucide-react';
import { useStore } from '../../store/useStore';
import { api } from '../../lib/api';
import type { MetricRecord, VerificationStatus } from '../../lib/types';

const STATUS_CONFIG: Record<VerificationStatus, { label: string; emoji: string; badgeClass: string }> = {
  verified: { label: 'Verified', emoji: '✅', badgeClass: 'badge-verified' },
  partially_verified: { label: 'Partial', emoji: '⚠️', badgeClass: 'badge-partial' },
  unverified: { label: 'Unverified', emoji: '❌', badgeClass: 'badge-unverified' },
  contradicted: { label: 'Contradicted', emoji: '🚫', badgeClass: 'badge-contradicted' },
  not_found: { label: 'Not Found', emoji: '❓', badgeClass: 'badge-notfound' },
};

export default function Dashboard() {
  const { projectId, metrics, summary, selectedMetric, setSelectedMetric, selectedSlide, setSelectedSlide } = useStore();
  const [filter, setFilter] = useState<VerificationStatus | 'all'>('all');
  const [sortCol, setSortCol] = useState<string>('slide');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  // Filtered & sorted metrics
  const filteredMetrics = useMemo(() => {
    let result = [...metrics];
    if (filter !== 'all') result = result.filter(m => m.verification?.status === filter);
    if (selectedSlide) result = result.filter(m => m.slide_number === selectedSlide);

    result.sort((a, b) => {
      let cmp = 0;
      if (sortCol === 'slide') cmp = a.slide_number - b.slide_number;
      else if (sortCol === 'confidence') cmp = (a.verification?.confidence_score ?? 0) - (b.verification?.confidence_score ?? 0);
      else if (sortCol === 'status') cmp = (a.verification?.status ?? '').localeCompare(b.verification?.status ?? '');
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return result;
  }, [metrics, filter, selectedSlide, sortCol, sortDir]);

  // Slide list
  const slideNumbers = useMemo(() => [...new Set(metrics.map(m => m.slide_number))].sort((a, b) => a - b), [metrics]);

  const getSlideStatus = (slideNum: number): VerificationStatus => {
    const slideMetrics = metrics.filter(m => m.slide_number === slideNum);
    if (slideMetrics.some(m => m.verification?.status === 'contradicted')) return 'contradicted';
    if (slideMetrics.some(m => m.verification?.status === 'unverified')) return 'unverified';
    if (slideMetrics.some(m => m.verification?.status === 'partially_verified')) return 'partially_verified';
    if (slideMetrics.some(m => m.verification?.status === 'not_found')) return 'not_found';
    return 'verified';
  };

  const toggleSort = (col: string) => {
    if (sortCol === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortCol(col); setSortDir('asc'); }
  };

  const overallAssessment = () => {
    if (!summary) return '';
    if (summary.contradicted > 0 || summary.unverified > 5) return '🔴 Significant gaps — requires manual audit';
    if (summary.partially_verified > 3 || summary.unverified > 0) return '🟡 Needs review';
    return '🟢 Ready for client';
  };

  return (
    <div className="flex-1 flex animate-fade-in">
      {/* Left sidebar — Slide navigator */}
      <div className="w-48 flex-shrink-0 border-r border-white/5 p-3 overflow-y-auto">
        <h3 className="text-xs font-semibold text-[var(--color-navy-500)] uppercase tracking-wider mb-3">Slides</h3>
        <button
          onClick={() => setSelectedSlide(null)}
          className={`w-full text-left text-xs p-2 rounded-lg mb-1 transition-colors ${!selectedSlide ? 'bg-[var(--color-electric)]/10 text-[var(--color-electric-light)]' : 'hover:bg-white/5 text-[var(--color-navy-400)]'}`}
        >
          All Slides
        </button>
        {slideNumbers.map(sn => {
          const status = getSlideStatus(sn);
          const count = metrics.filter(m => m.slide_number === sn).length;
          return (
            <button
              key={sn}
              onClick={() => setSelectedSlide(selectedSlide === sn ? null : sn)}
              className={`w-full text-left text-xs p-2 rounded-lg mb-1 flex items-center gap-2 transition-colors ${selectedSlide === sn ? 'bg-[var(--color-electric)]/10 text-[var(--color-electric-light)]' : 'hover:bg-white/5 text-[var(--color-navy-400)]'}`}
            >
              <div className={`w-2 h-2 rounded-full ${status === 'verified' ? 'bg-[var(--color-emerald)]' : status === 'partially_verified' ? 'bg-[var(--color-amber)]' : status === 'contradicted' ? 'bg-[var(--color-rose)]' : 'bg-[var(--color-orange)]'}`} />
              <span>Slide {sn}</span>
              <span className="ml-auto text-[var(--color-navy-600)]">{count}</span>
            </button>
          );
        })}
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Summary bar */}
        {summary && (
          <div className="p-4 border-b border-white/5">
            <div className="flex items-center gap-6 flex-wrap">
              <div className="flex items-center gap-2">
                <span className="text-2xl font-bold">{summary.total_metrics_extracted}</span>
                <span className="text-xs text-[var(--color-navy-500)]">metrics</span>
              </div>
              <div className="flex gap-3">
                {(['verified', 'partially_verified', 'unverified', 'contradicted', 'not_found'] as VerificationStatus[]).map(s => {
                  const count = summary[s === 'partially_verified' ? 'partially_verified' : s as keyof typeof summary] as number;
                  const cfg = STATUS_CONFIG[s];
                  return (
                    <button
                      key={s}
                      onClick={() => setFilter(filter === s ? 'all' : s)}
                      className={`badge ${cfg.badgeClass} cursor-pointer ${filter === s ? 'ring-1 ring-white/20' : ''}`}
                    >
                      {cfg.emoji} {count}
                    </button>
                  );
                })}
              </div>
              <div className="ml-auto flex items-center gap-3">
                <span className="text-xs text-[var(--color-navy-500)]">
                  Confidence: <strong className="text-[var(--color-navy-300)]">{(summary.avg_confidence_score * 100).toFixed(0)}%</strong>
                </span>
                <span className="text-xs">{overallAssessment()}</span>
              </div>
            </div>
            {/* Flags */}
            {summary.flags.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {summary.flags.map((f, i) => (
                  <span key={i} className="text-xs px-2 py-1 rounded bg-[var(--color-amber)]/10 text-[var(--color-amber)]">{f}</span>
                ))}
              </div>
            )}
            {/* Download buttons */}
            <div className="mt-3 flex gap-2">
              {projectId && (
                <>
                  <a href={api.downloadPptx(projectId)} className="btn-primary text-xs py-2 px-4">
                    <Download size={14} /> Annotated PPTX
                  </a>
                  <a href={api.downloadExcel(projectId)} className="btn-secondary text-xs py-2 px-4">
                    <Download size={14} /> Excel Report
                  </a>
                </>
              )}
            </div>
          </div>
        )}

        {/* Metric table */}
        <div className="flex-1 overflow-auto">
          <table className="audit-table">
            <thead>
              <tr>
                <th className="cursor-pointer" onClick={() => toggleSort('slide')}>Slide # {sortCol === 'slide' && (sortDir === 'asc' ? '↑' : '↓')}</th>
                <th>Metric</th>
                <th>Description</th>
                <th className="cursor-pointer" onClick={() => toggleSort('status')}>Status {sortCol === 'status' && (sortDir === 'asc' ? '↑' : '↓')}</th>
                <th className="cursor-pointer" onClick={() => toggleSort('confidence')}>Confidence {sortCol === 'confidence' && (sortDir === 'asc' ? '↑' : '↓')}</th>
                <th>Source</th>
                <th>Ultimate Source</th>
                <th>Reliability</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filteredMetrics.map(m => {
                const v = m.verification;
                const cfg = v ? STATUS_CONFIG[v.status] : null;
                return (
                  <tr key={m.metric_id} onClick={() => setSelectedMetric(m)} className="cursor-pointer">
                    <td className="font-mono text-[var(--color-navy-400)]">{m.slide_number}</td>
                    <td className="font-semibold text-[var(--color-navy-200)] max-w-[200px] truncate">{m.extracted_metric.value}</td>
                    <td className="text-[var(--color-navy-400)] max-w-[200px] truncate">{m.extracted_metric.description}</td>
                    <td>{cfg && <span className={`badge ${cfg.badgeClass}`}>{cfg.emoji} {cfg.label}</span>}</td>
                    <td className="font-mono text-sm">{v ? `${(v.confidence_score * 100).toFixed(0)}%` : '-'}</td>
                    <td className="text-[var(--color-navy-400)] max-w-[150px] truncate">{v?.matched_source_document_name || '-'}</td>
                    <td className="text-[var(--color-navy-400)] max-w-[150px] truncate">{v?.citation_chain?.ultimate_source || '-'}</td>
                    <td>
                      {v?.source_reliability && (
                        <span className="stars text-xs">{'★'.repeat(v.source_reliability.stars)}{'☆'.repeat(5 - v.source_reliability.stars)}</span>
                      )}
                    </td>
                    <td><ChevronRight size={14} className="text-[var(--color-navy-600)]" /></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Detail panel (slide-out) */}
      {selectedMetric && (
        <DetailPanel metric={selectedMetric} onClose={() => setSelectedMetric(null)} />
      )}
    </div>
  );
}

function DetailPanel({ metric, onClose }: { metric: MetricRecord; onClose: () => void }) {
  const v = metric.verification;

  return (
    <div className="w-96 flex-shrink-0 border-l border-white/5 bg-[var(--color-navy-900)] overflow-y-auto animate-fade-in">
      <div className="p-4 border-b border-white/5 flex items-center justify-between">
        <h3 className="font-semibold text-sm">Metric Detail</h3>
        <button onClick={onClose} className="p-1 rounded hover:bg-white/5"><X size={16} /></button>
      </div>

      <div className="p-4 space-y-5">
        {/* Metric info */}
        <div>
          <label className="text-xs text-[var(--color-navy-500)] uppercase tracking-wider">Metric Value</label>
          <p className="text-lg font-bold mt-1 gradient-text">{metric.extracted_metric.value}</p>
        </div>

        <div>
          <label className="text-xs text-[var(--color-navy-500)] uppercase tracking-wider">Description</label>
          <p className="text-sm mt-1">{metric.extracted_metric.description}</p>
        </div>

        <div>
          <label className="text-xs text-[var(--color-navy-500)] uppercase tracking-wider">Context</label>
          <p className="text-xs mt-1 text-[var(--color-navy-400)] italic">"{metric.extracted_metric.context_sentence}"</p>
        </div>

        <div className="text-xs text-[var(--color-navy-500)]">Slide {metric.slide_number} · Shape {metric.shape_id}</div>

        {v && (
          <>
            <hr className="border-white/5" />

            {/* Status */}
            <div>
              <label className="text-xs text-[var(--color-navy-500)] uppercase tracking-wider">Verification Status</label>
              <div className="mt-2 flex items-center gap-3">
                <span className={`badge ${STATUS_CONFIG[v.status].badgeClass} text-sm`}>
                  {STATUS_CONFIG[v.status].emoji} {STATUS_CONFIG[v.status].label}
                </span>
                <span className="text-sm font-mono">{(v.confidence_score * 100).toFixed(0)}%</span>
              </div>
            </div>

            {/* Source match */}
            {v.matched_location && (
              <div>
                <label className="text-xs text-[var(--color-navy-500)] uppercase tracking-wider">Source Match</label>
                <div className="mt-2 p-3 rounded-lg bg-white/[0.02] border border-white/5">
                  <p className="text-xs text-[var(--color-navy-400)] mb-1">
                    📄 {v.matched_source_document_name || 'Unknown'}
                    {v.matched_location.page_number && ` · Page ${v.matched_location.page_number}`}
                  </p>
                  {v.matched_location.section_heading && (
                    <p className="text-xs text-[var(--color-navy-500)] mb-2">§ {v.matched_location.section_heading}</p>
                  )}
                  {v.matched_location.exact_quote && (
                    <blockquote className="text-xs text-[var(--color-navy-300)] border-l-2 border-[var(--color-electric)]/30 pl-3 italic">
                      "{v.matched_location.exact_quote}"
                    </blockquote>
                  )}
                </div>
              </div>
            )}

            {/* Citation chain */}
            {v.citation_chain?.ultimate_source && (
              <div>
                <label className="text-xs text-[var(--color-navy-500)] uppercase tracking-wider">Citation Chain</label>
                <div className="mt-2 text-xs space-y-1">
                  {v.citation_chain.intermediate_source && (
                    <p>├─ <span className="text-[var(--color-navy-400)]">Found in:</span> {v.citation_chain.intermediate_source}</p>
                  )}
                  {v.citation_chain.intermediate_ref_id && (
                    <p>├─ <span className="text-[var(--color-navy-400)]">Ref:</span> {v.citation_chain.intermediate_ref_id}</p>
                  )}
                  <p>└─ <span className="text-[var(--color-navy-400)]">Original:</span> <strong>{v.citation_chain.ultimate_source}</strong></p>
                  {v.citation_chain.ultimate_source_type && (
                    <p className="pl-6 text-[var(--color-navy-500)]">Type: {v.citation_chain.ultimate_source_type}</p>
                  )}
                </div>
              </div>
            )}

            {/* Reliability */}
            {v.source_reliability && (
              <div>
                <label className="text-xs text-[var(--color-navy-500)] uppercase tracking-wider">Source Reliability</label>
                <div className="mt-2 p-3 rounded-lg bg-white/[0.02] border border-white/5">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="stars">{'★'.repeat(v.source_reliability.stars)}{'☆'.repeat(5 - v.source_reliability.stars)}</span>
                    <span className="text-xs font-semibold">{v.source_reliability.tier_label}</span>
                  </div>
                  <p className="text-xs text-[var(--color-navy-400)]">{v.source_reliability.reasoning}</p>
                  {v.source_reliability.recommendation && (
                    <p className="text-xs mt-2 text-[var(--color-amber)]">💡 {v.source_reliability.recommendation}</p>
                  )}
                </div>
              </div>
            )}

            {/* Notes */}
            {v.verification_notes && (
              <div>
                <label className="text-xs text-[var(--color-navy-500)] uppercase tracking-wider">Notes</label>
                <p className="text-xs mt-1 text-[var(--color-amber)]">⚠️ {v.verification_notes}</p>
              </div>
            )}

            {/* LLM Reasoning */}
            {v.llm_reasoning && (
              <div>
                <label className="text-xs text-[var(--color-navy-500)] uppercase tracking-wider">LLM Reasoning</label>
                <p className="text-xs mt-1 text-[var(--color-navy-400)]">{v.llm_reasoning}</p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
