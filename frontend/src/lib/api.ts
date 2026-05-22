// SourceLens API Client

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API Error ${res.status}`);
  }
  return res.json();
}

export const api = {
  // Projects
  createProject: (name: string) =>
    request('/projects', { method: 'POST', body: JSON.stringify({ project_name: name }) }),

  listProjects: () => request('/projects'),

  getProject: (id: string) => request(`/projects/${id}`),

  deleteProject: (id: string) =>
    request(`/projects/${id}`, { method: 'DELETE' }),

  // Files
  uploadPresentation: async (projectId: string, file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch(`${BASE}/projects/${projectId}/presentation`, {
      method: 'POST',
      body: fd,
    });
    if (!res.ok) throw new Error('Upload failed');
    return res.json();
  },

  uploadSource: async (projectId: string, file: File, label: string, docType: string) => {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('document_label', label);
    fd.append('document_type', docType);
    const res = await fetch(`${BASE}/projects/${projectId}/sources`, {
      method: 'POST',
      body: fd,
    });
    if (!res.ok) throw new Error('Upload failed');
    return res.json();
  },

  removeSource: (projectId: string, fileId: string) =>
    request(`/projects/${projectId}/sources/${fileId}`, { method: 'DELETE' }),

  getSlides: (projectId: string) => request(`/projects/${projectId}/slides`),

  // Analysis
  startAnalysis: (projectId: string) =>
    request(`/projects/${projectId}/analyze`, { method: 'POST' }),

  getStatus: (projectId: string) => request(`/projects/${projectId}/status`),

  getMetrics: (projectId: string) => request(`/projects/${projectId}/metrics`),

  getMetric: (projectId: string, metricId: string) =>
    request(`/projects/${projectId}/metrics/${metricId}`),

  overrideMetric: (projectId: string, metricId: string, data: any) =>
    request(`/projects/${projectId}/metrics/${metricId}`, { method: 'PATCH', body: JSON.stringify(data) }),

  getSummary: (projectId: string) => request(`/projects/${projectId}/summary`),

  getHeatmap: (projectId: string) => request(`/projects/${projectId}/heatmap`),

  // Downloads
  downloadPptx: (projectId: string) => `${BASE}/projects/${projectId}/download/pptx`,
  downloadExcel: (projectId: string) => `${BASE}/projects/${projectId}/download/excel`,

  // Config
  getConfig: () => request('/config'),

  updateConfig: (data: any) =>
    request('/config', { method: 'PUT', body: JSON.stringify(data) }),

  testApiKey: (key: string) =>
    request('/config/test-api-key', { method: 'POST', body: JSON.stringify({ openai_api_key: key }) }),
};
