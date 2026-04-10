import { useState, useEffect } from 'react';
import { X, Key, Check, AlertCircle, Sparkles, Zap } from 'lucide-react';
import { useStore } from '../../store/useStore';
import { api } from '../../lib/api';

interface ModelInfo {
  label: string;
  provider: string;
  cost_tier: string;
}

export default function SettingsDialog() {
  const { showSettings, setShowSettings, config, setConfig } = useStore();
  const [googleKey, setGoogleKey] = useState('');
  const [openaiKey, setOpenaiKey] = useState('');
  const [model, setModel] = useState('gemini-3.1-flash-lite');
  const [embeddingModel, setEmbeddingModel] = useState('models/text-embedding-004');
  const [strictness, setStrictness] = useState('standard');
  const [demoMode, setDemoMode] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{ valid: boolean; error?: string; provider?: string } | null>(null);
  const [saving, setSaving] = useState(false);
  const [availableModels, setAvailableModels] = useState<Record<string, ModelInfo>>({});

  useEffect(() => {
    if (showSettings) {
      api.getConfig().then((c: any) => {
        setConfig(c);
        setModel(c.llm_model);
        setEmbeddingModel(c.embedding_model);
        setStrictness(c.verification_strictness);
        setDemoMode(c.demo_mode || false);
        if (c.available_models) setAvailableModels(c.available_models);
      }).catch(() => {});
    }
  }, [showSettings]);

  const testKey = async (provider: string) => {
    const key = provider === 'gemini' ? googleKey : openaiKey;
    if (!key) return;
    setTesting(provider);
    setTestResult(null);
    try {
      const res = await fetch('/api/config/test-api-key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: key, provider }),
      }).then(r => r.json());
      setTestResult(res);
    } catch {
      setTestResult({ valid: false, error: 'Connection failed' });
    }
    setTesting(null);
  };

  const save = async () => {
    setSaving(true);
    try {
      const data: any = {
        llm_model: model,
        embedding_model: embeddingModel,
        verification_strictness: strictness,
        demo_mode: demoMode,
      };
      if (googleKey) data.google_api_key = googleKey;
      if (openaiKey) data.openai_api_key = openaiKey;
      await api.updateConfig(data);

      // Refresh config
      const c: any = await api.getConfig();
      setConfig(c);
      setShowSettings(false);
    } catch {}
    setSaving(false);
  };

  if (!showSettings) return null;

  // Group models by provider
  const geminiModels = Object.entries(availableModels).filter(([, v]) => v.provider === 'gemini');
  const openaiModels = Object.entries(availableModels).filter(([, v]) => v.provider === 'openai');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={() => setShowSettings(false)}>
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div
        className="relative glass-card w-full max-w-lg p-6 animate-slide-up max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-bold">Settings</h2>
          <button onClick={() => setShowSettings(false)} className="p-1 rounded hover:bg-white/5"><X size={18} /></button>
        </div>

        <div className="space-y-6">
          {/* Demo Mode Toggle */}
          <div className="p-3 rounded-lg bg-[var(--color-amber)]/5 border border-[var(--color-amber)]/20">
            <label className="flex items-center justify-between cursor-pointer">
              <div className="flex items-center gap-2">
                <Sparkles size={16} className="text-[var(--color-amber)]" />
                <span className="text-sm font-medium">Demo Mode</span>
                <span className="text-xs text-[var(--color-navy-500)]">(no API key needed)</span>
              </div>
              <div
                className={`w-10 h-5 rounded-full transition-colors relative cursor-pointer ${demoMode ? 'bg-[var(--color-amber)]' : 'bg-[var(--color-navy-700)]'}`}
                onClick={() => setDemoMode(!demoMode)}
              >
                <div
                  className={`w-4 h-4 rounded-full bg-white absolute top-0.5 transition-transform ${demoMode ? 'translate-x-5' : 'translate-x-0.5'}`}
                />
              </div>
            </label>
            <p className="text-xs text-[var(--color-navy-500)] mt-2">
              Uses regex-based metric extraction and text-matching verification. Great for demos and testing.
            </p>
          </div>

          {/* Google API Key */}
          <div>
            <label className="text-xs text-[var(--color-navy-400)] uppercase tracking-wider mb-2 flex items-center gap-2">
              <span className="w-4 h-4 rounded bg-blue-500/20 flex items-center justify-center text-[10px] font-bold text-blue-400">G</span>
              Google API Key
              {config?.has_google_key && <Check size={12} className="text-[var(--color-emerald)]" />}
            </label>
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <Key size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-navy-500)]" />
                <input
                  type="password"
                  value={googleKey}
                  onChange={(e) => setGoogleKey(e.target.value)}
                  placeholder={config?.has_google_key ? '••••••••••• (configured)' : 'AIza...'}
                  className="input pl-9"
                />
              </div>
              <button onClick={() => testKey('gemini')} disabled={!googleKey || testing === 'gemini'} className="btn-secondary text-xs">
                {testing === 'gemini' ? '...' : 'Test'}
              </button>
            </div>
            {testResult?.provider === 'gemini' && (
              <p className={`text-xs mt-1 flex items-center gap-1 ${testResult.valid ? 'text-[var(--color-emerald)]' : 'text-[var(--color-rose)]'}`}>
                {testResult.valid ? <><Check size={12} /> Valid</> : <><AlertCircle size={12} /> {testResult.error}</>}
              </p>
            )}
          </div>

          {/* OpenAI API Key */}
          <div>
            <label className="text-xs text-[var(--color-navy-400)] uppercase tracking-wider mb-2 flex items-center gap-2">
              <span className="w-4 h-4 rounded bg-emerald-500/20 flex items-center justify-center text-[10px] font-bold text-emerald-400">O</span>
              OpenAI API Key
              {config?.has_openai_key && <Check size={12} className="text-[var(--color-emerald)]" />}
            </label>
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <Key size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-navy-500)]" />
                <input
                  type="password"
                  value={openaiKey}
                  onChange={(e) => setOpenaiKey(e.target.value)}
                  placeholder={config?.has_openai_key ? '••••••••••• (configured)' : 'sk-...'}
                  className="input pl-9"
                />
              </div>
              <button onClick={() => testKey('openai')} disabled={!openaiKey || testing === 'openai'} className="btn-secondary text-xs">
                {testing === 'openai' ? '...' : 'Test'}
              </button>
            </div>
            {testResult?.provider === 'openai' && (
              <p className={`text-xs mt-1 flex items-center gap-1 ${testResult.valid ? 'text-[var(--color-emerald)]' : 'text-[var(--color-rose)]'}`}>
                {testResult.valid ? <><Check size={12} /> Valid</> : <><AlertCircle size={12} /> {testResult.error}</>}
              </p>
            )}
          </div>

          {/* Model Selection */}
          <div>
            <label className="text-xs text-[var(--color-navy-400)] uppercase tracking-wider mb-2 block">
              LLM Model
            </label>
            <select value={model} onChange={(e) => setModel(e.target.value)} className="input">
              {geminiModels.length > 0 && (
                <optgroup label="Google Gemini">
                  {geminiModels.map(([key, info]) => (
                    <option key={key} value={key}>
                      {info.label} {info.cost_tier === 'budget' ? '💰' : '💎'}
                    </option>
                  ))}
                </optgroup>
              )}
              {openaiModels.length > 0 && (
                <optgroup label="OpenAI">
                  {openaiModels.map(([key, info]) => (
                    <option key={key} value={key}>
                      {info.label} {info.cost_tier === 'budget' ? '💰' : '💎'}
                    </option>
                  ))}
                </optgroup>
              )}
            </select>
            <p className="text-xs text-[var(--color-navy-500)] mt-1 flex items-center gap-1">
              <Zap size={10} />
              {model.startsWith('gemini') ? 'Requires Google API key' : 'Requires OpenAI API key'}
            </p>
          </div>

          {/* Embedding model */}
          <div>
            <label className="text-xs text-[var(--color-navy-400)] uppercase tracking-wider mb-2 block">Embedding Model</label>
            <select value={embeddingModel} onChange={(e) => setEmbeddingModel(e.target.value)} className="input">
              <optgroup label="Google">
                <option value="models/text-embedding-004">text-embedding-004 (Gemini)</option>
              </optgroup>
              <optgroup label="OpenAI">
                <option value="text-embedding-3-small">text-embedding-3-small</option>
                <option value="text-embedding-3-large">text-embedding-3-large</option>
              </optgroup>
            </select>
          </div>

          {/* Strictness */}
          <div>
            <label className="text-xs text-[var(--color-navy-400)] uppercase tracking-wider mb-2 block">
              Verification Strictness: <strong className="text-[var(--color-navy-200)] capitalize">{strictness}</strong>
            </label>
            <input
              type="range"
              min="0"
              max="2"
              value={strictness === 'lenient' ? 0 : strictness === 'standard' ? 1 : 2}
              onChange={(e) => setStrictness(['lenient', 'standard', 'strict'][parseInt(e.target.value)])}
              className="w-full accent-[var(--color-electric)]"
            />
            <div className="flex justify-between text-xs text-[var(--color-navy-600)]">
              <span>Lenient</span><span>Standard</span><span>Strict</span>
            </div>
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button onClick={() => setShowSettings(false)} className="btn-secondary">Cancel</button>
          <button onClick={save} disabled={saving} className="btn-primary">
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </div>
    </div>
  );
}
