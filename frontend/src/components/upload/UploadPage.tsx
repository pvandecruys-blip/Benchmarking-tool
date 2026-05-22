import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, X, Sparkles } from 'lucide-react';
import { useStore } from '../../store/useStore';
import { api } from '../../lib/api';
import type { DocumentType } from '../../lib/types';

const DOC_TYPES: { value: DocumentType; label: string }[] = [
  { value: 'deep_research_report', label: 'Deep Research Report' },
  { value: 'article', label: 'Industry Article' },
  { value: 'whitepaper', label: 'Whitepaper / Thought Leadership' },
  { value: 'market_research', label: 'Market Research' },
  { value: 'regulatory_document', label: 'Regulatory Document' },
  { value: 'internal_analysis', label: 'Internal Analysis' },
  { value: 'other', label: 'Other' },
];

export default function UploadPage() {
  const {
    projectId, setProject, setView,
    presentationInfo, setPresentationInfo,
    sourceDocs, addSourceDoc, removeSourceDoc,
  } = useStore();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [docLabel, setDocLabel] = useState('');
  const [docType, setDocType] = useState<DocumentType>('deep_research_report');

  // Ensure project exists
  const ensureProject = async () => {
    if (projectId) return projectId;
    const res: any = await api.createProject('New Analysis');
    setProject(res.project_id, res.project_name);
    return res.project_id;
  };

  // PPTX Upload
  const onPptxDrop = useCallback(async (files: File[]) => {
    const file = files[0];
    if (!file) return;
    setError('');
    setLoading(true);
    try {
      const pid = await ensureProject();
      const res: any = await api.uploadPresentation(pid, file);
      setPresentationInfo({
        filename: res.filename,
        slideCount: res.slide_count,
        sizeBytes: res.size_bytes,
      });
    } catch (e: any) {
      setError(e.message);
    }
    setLoading(false);
  }, [projectId]);

  const { getRootProps: getPptxRootProps, getInputProps: getPptxInputProps, isDragActive: isPptxDragActive } =
    useDropzone({ onDrop: onPptxDrop, accept: { 'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'] }, maxFiles: 1 });

  // Source doc upload
  const onSourceDrop = useCallback(async (files: File[]) => {
    setError('');
    setLoading(true);
    try {
      const pid = await ensureProject();
      for (const file of files) {
        const label = docLabel || file.name.replace(/\.[^.]+$/, '');
        const res: any = await api.uploadSource(pid, file, label, docType);
        addSourceDoc({
          file_id: res.file_id,
          original_filename: res.filename,
          document_label: res.document_label,
          document_type: res.document_type,
          file_size_bytes: res.size_bytes,
        });
      }
      setDocLabel('');
    } catch (e: any) {
      setError(e.message);
    }
    setLoading(false);
  }, [projectId, docLabel, docType]);

  const { getRootProps: getSrcRootProps, getInputProps: getSrcInputProps, isDragActive: isSrcDragActive } =
    useDropzone({ onDrop: onSourceDrop, accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/markdown': ['.md'],
      'text/plain': ['.txt'],
    }});

  // Start analysis
  const startAnalysis = async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      await api.startAnalysis(projectId);
      setView('processing');
    } catch (e: any) {
      setError(e.message);
    }
    setLoading(false);
  };

  const ready = presentationInfo && sourceDocs.length > 0;

  const formatSize = (bytes: number) => {
    if (bytes > 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
    return `${(bytes / 1024).toFixed(0)} KB`;
  };

  return (
    <div className="flex-1 p-6 animate-fade-in">
      <div className="max-w-6xl mx-auto">
        {/* Title */}
        <div className="text-center mb-8">
          <h2 className="text-3xl font-bold mb-2">
            <span className="gradient-text">Upload & Analyse</span>
          </h2>
          <p className="text-[var(--color-navy-400)] text-sm">
            Upload your presentation and source documents to begin the audit
          </p>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-[var(--color-rose)]/10 border border-[var(--color-rose)]/20 text-[var(--color-rose-light)] text-sm">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* LEFT: Presentation Upload */}
          <div className="glass-card p-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Upload size={20} className="text-[var(--color-electric)]" />
              Presentation
              <span className="text-xs text-[var(--color-navy-500)] font-normal">.pptx</span>
            </h3>

            {!presentationInfo ? (
              <div
                {...getPptxRootProps()}
                className={`dropzone ${isPptxDragActive ? 'dropzone-active' : ''}`}
              >
                <input {...getPptxInputProps()} />
                <Upload size={40} className="mx-auto mb-3 text-[var(--color-navy-500)]" />
                <p className="text-sm text-[var(--color-navy-400)]">
                  {isPptxDragActive ? 'Drop your PPTX file here...' : 'Drag & drop your PowerPoint file, or click to browse'}
                </p>
                <p className="text-xs text-[var(--color-navy-600)] mt-2">Max 100 MB</p>
              </div>
            ) : (
              <div className="p-4 rounded-lg bg-[var(--color-electric)]/5 border border-[var(--color-electric)]/20">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-[var(--color-electric)]/10 flex items-center justify-center">
                    <FileText size={20} className="text-[var(--color-electric)]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm truncate">{presentationInfo.filename}</p>
                    <p className="text-xs text-[var(--color-navy-400)]">
                      {presentationInfo.slideCount} slides · {formatSize(presentationInfo.sizeBytes)}
                    </p>
                  </div>
                  <button
                    onClick={() => setPresentationInfo(null)}
                    className="p-1 rounded hover:bg-white/5"
                  >
                    <X size={16} className="text-[var(--color-navy-500)]" />
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* RIGHT: Source Documents */}
          <div className="glass-card p-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <FileText size={20} className="text-[var(--color-emerald)]" />
              Source Documents
              <span className="text-xs text-[var(--color-navy-500)] font-normal">.pdf .docx .md .txt</span>
            </h3>

            {/* Label & Type inputs */}
            <div className="grid grid-cols-2 gap-3 mb-3">
              <input
                type="text"
                placeholder="Document label (optional)"
                value={docLabel}
                onChange={(e) => setDocLabel(e.target.value)}
                className="input text-xs"
              />
              <select
                value={docType}
                onChange={(e) => setDocType(e.target.value as DocumentType)}
                className="input text-xs"
              >
                {DOC_TYPES.map(dt => (
                  <option key={dt.value} value={dt.value}>{dt.label}</option>
                ))}
              </select>
            </div>

            <div
              {...getSrcRootProps()}
              className={`dropzone mb-4 ${isSrcDragActive ? 'dropzone-active' : ''}`}
              style={{ padding: '24px' }}
            >
              <input {...getSrcInputProps()} />
              <Upload size={32} className="mx-auto mb-2 text-[var(--color-navy-500)]" />
              <p className="text-sm text-[var(--color-navy-400)]">
                {isSrcDragActive ? 'Drop files here...' : 'Drop source documents here or click to browse'}
              </p>
            </div>

            {/* Uploaded docs list */}
            {sourceDocs.length > 0 && (
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {sourceDocs.map((doc) => (
                  <div key={doc.file_id} className="flex items-center gap-3 p-3 rounded-lg bg-white/[0.02] border border-white/5">
                    <div className="w-8 h-8 rounded bg-[var(--color-emerald)]/10 flex items-center justify-center flex-shrink-0">
                      <FileText size={14} className="text-[var(--color-emerald)]" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{doc.document_label || doc.original_filename}</p>
                      <p className="text-xs text-[var(--color-navy-500)]">
                        {doc.document_type.replace(/_/g, ' ')} · {formatSize(doc.file_size_bytes)}
                      </p>
                    </div>
                    <button
                      onClick={() => removeSourceDoc(doc.file_id)}
                      className="p-1 rounded hover:bg-white/5"
                    >
                      <X size={14} className="text-[var(--color-navy-500)]" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Analyse button */}
        <div className="mt-8 text-center">
          <button
            onClick={startAnalysis}
            disabled={!ready || loading}
            className={`btn-primary text-base px-12 py-3 ${ready ? 'animate-pulse-glow' : ''}`}
          >
            <Sparkles size={20} />
            {loading ? 'Starting...' : 'Analyse'}
          </button>
          {!ready && (
            <p className="text-xs text-[var(--color-navy-500)] mt-3">
              Upload at least 1 presentation + 1 source document to begin
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
