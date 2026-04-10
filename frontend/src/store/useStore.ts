// SourceLens State Management — Zustand Store

import { create } from 'zustand';
import type { ProjectSummary, MetricRecord, AuditSummary, ProcessingStatus, SlidePreview, SourceDoc, AppConfig } from '../lib/types';

type AppView = 'upload' | 'processing' | 'results';

interface AppState {
  // Navigation
  view: AppView;
  setView: (v: AppView) => void;

  // Project
  projectId: string | null;
  projectName: string;
  setProject: (id: string, name: string) => void;

  // Upload state
  presentationFile: File | null;
  presentationInfo: { filename: string; slideCount: number; sizeBytes: number } | null;
  sourceDocs: SourceDoc[];
  setPresentationFile: (file: File | null) => void;
  setPresentationInfo: (info: any) => void;
  addSourceDoc: (doc: SourceDoc) => void;
  removeSourceDoc: (fileId: string) => void;

  // Slides
  slides: SlidePreview[];
  setSlides: (s: SlidePreview[]) => void;

  // Processing
  processingStatus: ProcessingStatus | null;
  setProcessingStatus: (s: ProcessingStatus) => void;

  // Results
  metrics: MetricRecord[];
  summary: AuditSummary | null;
  selectedMetric: MetricRecord | null;
  selectedSlide: number | null;
  setMetrics: (m: MetricRecord[]) => void;
  setSummary: (s: AuditSummary) => void;
  setSelectedMetric: (m: MetricRecord | null) => void;
  setSelectedSlide: (n: number | null) => void;

  // Settings
  showSettings: boolean;
  config: AppConfig | null;
  setShowSettings: (show: boolean) => void;
  setConfig: (c: AppConfig) => void;

  // Reset
  reset: () => void;
}

export const useStore = create<AppState>((set) => ({
  view: 'upload',
  setView: (v) => set({ view: v }),

  projectId: null,
  projectName: 'Untitled Project',
  setProject: (id, name) => set({ projectId: id, projectName: name }),

  presentationFile: null,
  presentationInfo: null,
  sourceDocs: [],
  setPresentationFile: (file) => set({ presentationFile: file }),
  setPresentationInfo: (info) => set({ presentationInfo: info }),
  addSourceDoc: (doc) => set((s) => ({ sourceDocs: [...s.sourceDocs, doc] })),
  removeSourceDoc: (fileId) => set((s) => ({ sourceDocs: s.sourceDocs.filter(d => d.file_id !== fileId) })),

  slides: [],
  setSlides: (slides) => set({ slides }),

  processingStatus: null,
  setProcessingStatus: (status) => set({ processingStatus: status }),

  metrics: [],
  summary: null,
  selectedMetric: null,
  selectedSlide: null,
  setMetrics: (m) => set({ metrics: m }),
  setSummary: (s) => set({ summary: s }),
  setSelectedMetric: (m) => set({ selectedMetric: m }),
  setSelectedSlide: (n) => set({ selectedSlide: n }),

  showSettings: false,
  config: null,
  setShowSettings: (show) => set({ showSettings: show }),
  setConfig: (c) => set({ config: c }),

  reset: () => set({
    view: 'upload',
    projectId: null,
    projectName: 'Untitled Project',
    presentationFile: null,
    presentationInfo: null,
    sourceDocs: [],
    slides: [],
    processingStatus: null,
    metrics: [],
    summary: null,
    selectedMetric: null,
    selectedSlide: null,
  }),
}));
