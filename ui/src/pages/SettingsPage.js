/**
 * ui/src/pages/SettingsPage.js
 * ============================
 * Multi-Tenant BYOK (Bring Your Own Key) Vault, System health diagnostics,
 * GPU hardware acceleration, and storage monitors.
 * Redesigned with Charcoal & Electric Lime design system.
 */

import { html, useState, useEffect } from '../html.js';
import { Icon } from '../components/Icons.js';
import { api } from '../api/client.js';

const PROVIDERS = [
  { id: 'groq', label: 'Groq Cloud', desc: 'Llama 3.3 / Ultra-fast inference', placeholder: 'gsk_...' },
  { id: 'gemini', label: 'Google Gemini', desc: 'Flash & Flash-Lite / Multimodal analysis', placeholder: 'AIzaSy...' },
  { id: 'openrouter', label: 'OpenRouter', desc: 'Multi-model fallback aggregator', placeholder: 'sk-or-v1-...' },
  { id: 'pexels', label: 'Pexels API', desc: 'HD portrait stock footage', placeholder: 'Pexels API Key...' },
  { id: 'elevenlabs', label: 'ElevenLabs', desc: 'Neural voiceover synthesis', placeholder: 'xi-api-key...' },
];

const PROVIDER_COLORS = {
  groq: 'text-status-warning bg-status-warning/10 border-status-warning/30',
  gemini: 'text-status-success bg-status-success/10 border-status-success/30',
  openrouter: 'text-lime-primary bg-lime-primary/10 border-lime-primary/30',
  pexels: 'text-sky-400 bg-sky-500/10 border-sky-500/30',
  elevenlabs: 'text-lime-secondary bg-lime-secondary/10 border-lime-secondary/30',
};

export function SettingsPage() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  // BYOK State
  const [keys, setKeys] = useState([]);
  const [keysLoading, setKeysLoading] = useState(true);
  const [selectedProvider, setSelectedProvider] = useState('groq');
  const [keyAlias, setKeyAlias] = useState('');
  const [rawKey, setRawKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [testStatus, setTestStatus] = useState(null);
  const [actionAlert, setActionAlert] = useState(null);

  const loadKeys = () => {
    setKeysLoading(true);
    api.keys.list()
      .then(setKeys)
      .catch((err) => console.error("Failed to load BYOK keys:", err))
      .finally(() => setKeysLoading(false));
  };

  useEffect(() => {
    Promise.all([
      api.system.getHealth().then(setHealth).catch((err) => console.error(err)),
      api.keys.list().then(setKeys).catch((err) => console.error(err))
    ]).finally(() => {
      setLoading(false);
      setKeysLoading(false);
    });
  }, []);

  const handleTestKey = async () => {
    if (!rawKey.trim()) {
      setActionAlert({ type: 'error', text: 'Please enter an API key to test.' });
      return;
    }
    setIsTesting(true);
    setTestStatus(null);
    setActionAlert(null);

    try {
      const res = await api.keys.validate({
        provider: selectedProvider,
        api_key: rawKey.trim()
      });
      setTestStatus(res);
      if (res.valid) {
        setActionAlert({ type: 'success', text: `Key verified: ${res.message}` });
      } else {
        setActionAlert({ type: 'error', text: `Validation failed: ${res.message}` });
      }
    } catch (err) {
      setTestStatus({ valid: false, message: err.message });
      setActionAlert({ type: 'error', text: `Validation error: ${err.message}` });
    } finally {
      setIsTesting(false);
    }
  };

  const handleSaveKey = async (e) => {
    e.preventDefault();
    if (!rawKey.trim()) {
      setActionAlert({ type: 'error', text: 'API Key is required.' });
      return;
    }
    setIsSaving(true);
    setActionAlert(null);

    try {
      await api.keys.add({
        provider: selectedProvider,
        api_key: rawKey.trim(),
        key_alias: keyAlias.trim() || undefined
      });
      setActionAlert({ type: 'success', text: 'API key validated, encrypted with AES-256-GCM, and stored securely!' });
      setRawKey('');
      setKeyAlias('');
      setTestStatus(null);
      loadKeys();
    } catch (err) {
      setActionAlert({ type: 'error', text: `Failed to save key: ${err.message}` });
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteKey = async (id, preview) => {
    if (!window.confirm(`Revoke and remove key (${preview})? This action cannot be undone.`)) {
      return;
    }
    try {
      await api.keys.delete(id);
      setActionAlert({ type: 'success', text: 'API key revoked and removed successfully.' });
      loadKeys();
    } catch (err) {
      setActionAlert({ type: 'error', text: `Failed to delete key: ${err.message}` });
    }
  };

  const activeProviderMeta = PROVIDERS.find((p) => p.id === selectedProvider) || PROVIDERS[0];

  return html`
    <div class="p-4 sm:p-6 lg:p-8 space-y-6 sm:space-y-8 max-w-7xl mx-auto w-full">
      <!-- Header -->
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 class="text-xl font-bold text-charcoal-100 flex items-center space-x-2">
            <${Icon} name="settings" className="w-5 h-5 text-lime-primary" />
            <span>Settings & BYOK Vault</span>
          </h2>
          <p class="text-xs text-charcoal-200 mt-1">
            Manage your personal AI keys, security isolation, pipeline storage, and acceleration engines.
          </p>
        </div>
        <div class="flex items-center gap-2">
          <span class="inline-flex items-center px-3 py-1 rounded-md text-[11px] font-semibold bg-lime-primary/10 text-lime-primary border border-lime-primary/25">
            <${Icon} name="shield" className="w-3.5 h-3.5 mr-1.5" />
            AES-256-GCM Encrypted
          </span>
        </div>
      </div>

      <!-- Action Feedback Banner -->
      ${actionAlert && html`
        <div class="p-4 rounded-xl text-xs flex items-center justify-between transition-all ${
          actionAlert.type === 'success'
            ? 'bg-charcoal-700 border border-status-success/40 text-status-success'
            : 'bg-charcoal-700 border border-status-error/40 text-status-error'
        }">
          <div class="flex items-center space-x-2">
            <${Icon} name="${actionAlert.type === 'success' ? 'check-circle' : 'alert-circle'}" className="w-4 h-4 flex-shrink-0" />
            <span>${actionAlert.text}</span>
          </div>
          <button
            onClick=${() => setActionAlert(null)}
            class="text-charcoal-300 hover:text-charcoal-100 ml-3"
          >
            <${Icon} name="close" className="w-3.5 h-3.5" />
          </button>
        </div>
      `}

      <!-- SECTION 1: Bring Your Own Key (BYOK) Management -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <!-- Add Key Form -->
        <div class="lg:col-span-5 bg-charcoal-700 border border-charcoal-500 rounded-xl p-5 sm:p-6 space-y-4">
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-bold text-charcoal-100 flex items-center space-x-2">
              <${Icon} name="key" className="w-4 h-4 text-lime-primary" />
              <span>Add Custom API Key</span>
            </h3>
            <span class="text-[10px] text-charcoal-300 font-mono">Preflight Verified</span>
          </div>

          <form onSubmit=${handleSaveKey} class="space-y-3.5">
            <!-- Provider Selector -->
            <div>
              <label class="block text-xs font-semibold text-charcoal-200 mb-1.5">AI / Media Provider</label>
              <select
                value=${selectedProvider}
                onChange=${(e) => {
                  setSelectedProvider(e.target.value);
                  setTestStatus(null);
                }}
                class="w-full bg-charcoal-800 border border-charcoal-500 rounded-lg px-3 py-2 text-xs text-charcoal-100 focus:outline-none focus:border-lime-primary focus:ring-1 focus:ring-lime-primary transition"
              >
                ${PROVIDERS.map((p) => html`
                  <option key=${p.id} value=${p.id}>${p.label} - ${p.desc}</option>
                `)}
              </select>
            </div>

            <!-- Key Alias -->
            <div>
              <label class="block text-xs font-semibold text-charcoal-200 mb-1.5">Key Alias (Optional)</label>
              <input
                type="text"
                placeholder="e.g. My Primary Key, Work Account"
                value=${keyAlias}
                onInput=${(e) => setKeyAlias(e.target.value)}
                class="w-full bg-charcoal-800 border border-charcoal-500 rounded-lg px-3 py-2 text-xs text-charcoal-100 placeholder-charcoal-300 focus:outline-none focus:border-lime-primary focus:ring-1 focus:ring-lime-primary transition"
              />
            </div>

            <!-- Raw API Key (with visibility toggle) -->
            <div>
              <label class="block text-xs font-semibold text-charcoal-200 mb-1.5">Secret Key</label>
              <div class="relative">
                <input
                  type=${showKey ? 'text' : 'password'}
                  placeholder=${activeProviderMeta.placeholder}
                  value=${rawKey}
                  onInput=${(e) => {
                    setRawKey(e.target.value);
                    setTestStatus(null);
                  }}
                  class="w-full bg-charcoal-800 border border-charcoal-500 rounded-lg pl-3 pr-10 py-2 text-xs font-mono text-charcoal-100 placeholder-charcoal-300 focus:outline-none focus:border-lime-primary focus:ring-1 focus:ring-lime-primary transition"
                  required
                />
                <button
                  type="button"
                  onClick=${() => setShowKey(!showKey)}
                  class="absolute right-2.5 top-1/2 -translate-y-1/2 text-charcoal-300 hover:text-charcoal-100 transition"
                  title=${showKey ? 'Hide key' : 'Show key'}
                >
                  <${Icon} name="eye" className="w-4 h-4" />
                </button>
              </div>
              <p class="text-[10px] text-charcoal-300 mt-1">
                Keys are authenticated live before persisting. Zero plaintext is ever logged or stored.
              </p>
            </div>

            <!-- Preflight Result Pill -->
            ${testStatus && html`
              <div class="p-2.5 rounded-lg text-xs flex items-center space-x-2 ${
                testStatus.valid
                  ? 'bg-charcoal-800 text-status-success border border-status-success/30'
                  : 'bg-charcoal-800 text-status-error border border-status-error/30'
              }">
                <${Icon} name="${testStatus.valid ? 'check' : 'alert-circle'}" className="w-3.5 h-3.5 flex-shrink-0" />
                <span class="text-[11px] font-medium">${testStatus.message}</span>
              </div>
            `}

            <!-- Buttons -->
            <div class="pt-2 flex items-center gap-3">
              <button
                type="button"
                onClick=${handleTestKey}
                disabled=${isTesting || isSaving || !rawKey.trim()}
                class="flex-1 px-4 py-2 bg-charcoal-600 hover:bg-charcoal-500 disabled:opacity-50 disabled:cursor-not-allowed text-charcoal-100 text-xs font-semibold rounded-lg border border-charcoal-500 transition flex items-center justify-center space-x-1.5"
              >
                ${isTesting ? html`
                  <span class="inline-block animate-spin mr-1">↻</span>
                  <span>Verifying...</span>
                ` : html`
                  <${Icon} name="zap" className="w-3.5 h-3.5 text-lime-primary" />
                  <span>Test Key</span>
                `}
              </button>

              <button
                type="submit"
                disabled=${isSaving || !rawKey.trim()}
                class="flex-1 px-4 py-2 bg-lime-primary hover:bg-lime-secondary disabled:opacity-50 disabled:cursor-not-allowed text-charcoal-900 text-xs font-bold rounded-lg transition active:scale-95 flex items-center justify-center space-x-1.5"
              >
                ${isSaving ? html`
                  <span class="inline-block animate-spin mr-1">↻</span>
                  <span>Encrypting...</span>
                ` : html`
                  <${Icon} name="check" className="w-3.5 h-3.5" />
                  <span>Save Key</span>
                `}
              </button>
            </div>
          </form>
        </div>

        <!-- Saved Keys List -->
        <div class="lg:col-span-7 bg-charcoal-700 border border-charcoal-500 rounded-xl p-5 sm:p-6 space-y-4 flex flex-col justify-between">
          <div>
            <div class="flex items-center justify-between mb-3">
              <h3 class="text-sm font-bold text-charcoal-100 flex items-center space-x-2">
                <${Icon} name="shield" className="w-4 h-4 text-lime-primary" />
                <span>Your Configured Keys</span>
              </h3>
              <button
                onClick=${loadKeys}
                class="text-xs text-charcoal-300 hover:text-charcoal-100 flex items-center space-x-1 transition"
                title="Refresh Keys"
              >
                <${Icon} name="refresh" className="w-3.5 h-3.5" />
                <span>Refresh</span>
              </button>
            </div>

            ${keysLoading ? html`
              <div class="p-12 text-center text-charcoal-300 text-xs">Loading encrypted keys...</div>
            ` : keys.length === 0 ? html`
              <div class="p-8 rounded-lg bg-charcoal-800 border border-charcoal-500 text-center space-y-3">
                <div class="w-10 h-10 rounded-lg bg-charcoal-700 border border-charcoal-500 flex items-center justify-center mx-auto text-charcoal-300">
                  <${Icon} name="key" className="w-5 h-5" />
                </div>
                <div class="space-y-1">
                  <div class="text-xs font-bold text-charcoal-100">No Personal API Keys Added</div>
                  <p class="text-[11px] text-charcoal-300 max-w-sm mx-auto">
                    Your video generation tasks are currently using shared system quotas. Add your own keys above for dedicated rate limits and higher throughput.
                  </p>
                </div>
              </div>
            ` : html`
              <div class="space-y-2.5 max-h-[340px] overflow-y-auto pr-1">
                ${keys.map((k) => html`
                  <div key=${k.id} class="p-3 rounded-lg bg-charcoal-800 border border-charcoal-500 flex items-center justify-between hover:border-charcoal-400 transition">
                    <div class="flex items-center space-x-3 min-w-0">
                      <span class="px-2.5 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider border ${PROVIDER_COLORS[k.provider] || 'text-charcoal-200 bg-charcoal-700 border-charcoal-500'}">
                        ${k.provider}
                      </span>
                      <div class="truncate">
                        <div class="font-bold text-xs text-charcoal-100 truncate flex items-center space-x-2">
                          <span>${k.key_alias || `${k.provider.toUpperCase()} Key`}</span>
                          <span class="inline-block w-1.5 h-1.5 rounded-full bg-status-success"></span>
                        </div>
                        <div class="text-[11px] font-mono text-charcoal-300 truncate">
                          ${k.key_preview}
                        </div>
                      </div>
                    </div>

                    <div class="flex items-center space-x-3 flex-shrink-0 ml-3">
                      <span class="text-[10px] text-charcoal-300 hidden sm:inline-block font-mono">
                        ${k.created_at ? new Date(k.created_at).toLocaleDateString() : ''}
                      </span>
                      <button
                        onClick=${() => handleDeleteKey(k.id, k.key_preview)}
                        class="p-1.5 text-charcoal-300 hover:text-status-error hover:bg-status-error/10 rounded-md transition"
                        title="Revoke & Delete Key"
                      >
                        <${Icon} name="trash" className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                `)}
              </div>
            `}
          </div>

          <!-- Bottom Notice -->
          <div class="pt-4 border-t border-charcoal-500 flex items-center justify-between text-[11px] text-charcoal-300">
            <span class="flex items-center space-x-1.5">
              <${Icon} name="shield" className="w-3.5 h-3.5 text-status-success" />
              <span>User keys take precedence; system keys serve as automatic fallback.</span>
            </span>
          </div>
        </div>
      </div>

      <!-- SECTION 2: System Health & Hardware Diagnostics -->
      <div>
        <h3 class="text-sm font-bold text-charcoal-100 flex items-center space-x-2 mb-4">
          <${Icon} name="activity" className="w-4 h-4 text-lime-primary" />
          <span>System Environment & Hardware Diagnostics</span>
        </h3>

        ${loading ? html`
          <div class="p-12 text-center text-charcoal-300 text-xs">Inspecting system health...</div>
        ` : !health ? html`
          <div class="p-6 text-center text-status-error text-xs">Failed to load system diagnostics.</div>
        ` : html`
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
            <!-- Global Key Rotation Pool -->
            <div class="bg-charcoal-700 border border-charcoal-500 rounded-xl p-5 sm:p-6 space-y-4">
              <h4 class="text-xs font-bold uppercase tracking-wider text-charcoal-300">
                System Global Fallback Pools
              </h4>

              <div class="space-y-3 text-xs">
                <div class="p-3.5 rounded-lg bg-charcoal-800 border border-charcoal-500 flex items-center justify-between">
                  <div>
                    <div class="font-bold text-charcoal-100">Groq API Pool</div>
                    <div class="text-[10px] text-charcoal-300">Primary model cascade (14,400 free req/day)</div>
                  </div>
                  <span class="px-2.5 py-1 rounded-md bg-lime-primary/15 text-lime-primary font-bold text-xs border border-lime-primary/30">
                    ${health.groq_keys_count} Active
                  </span>
                </div>

                <div class="p-3.5 rounded-lg bg-charcoal-800 border border-charcoal-500 flex items-center justify-between">
                  <div>
                    <div class="font-bold text-charcoal-100">Gemini API Pool</div>
                    <div class="text-[10px] text-charcoal-300">Automatic fallback & VLM review engine</div>
                  </div>
                  <span class="px-2.5 py-1 rounded-md bg-status-success/15 text-status-success font-bold text-xs border border-status-success/30">
                    ${health.gemini_keys_count} Active
                  </span>
                </div>

                <div class="p-3.5 rounded-lg bg-charcoal-800 border border-charcoal-500 flex items-center justify-between">
                  <div>
                    <div class="font-bold text-charcoal-100">OpenRouter Pool</div>
                    <div class="text-[10px] text-charcoal-300">Deep backup open-source models</div>
                  </div>
                  <span class="px-2.5 py-1 rounded-md bg-charcoal-700 text-charcoal-200 font-bold text-xs border border-charcoal-500">
                    ${health.openrouter_keys_count} Active
                  </span>
                </div>

                <div class="p-3.5 rounded-lg bg-charcoal-800 border border-charcoal-500 flex items-center justify-between">
                  <div>
                    <div class="font-bold text-charcoal-100">Pexels Stock Video Pool</div>
                    <div class="text-[10px] text-charcoal-300">High-resolution B-roll footage retrieval</div>
                  </div>
                  <span class="px-2.5 py-1 rounded-md bg-sky-500/15 text-sky-400 font-bold text-xs border border-sky-500/30">
                    ${health.pexels_keys_count} Active
                  </span>
                </div>
              </div>
            </div>

            <!-- Hardware & Engine Diagnostics -->
            <div class="bg-charcoal-700 border border-charcoal-500 rounded-xl p-5 sm:p-6 space-y-4">
              <h4 class="text-xs font-bold uppercase tracking-wider text-charcoal-300">
                Hardware Acceleration & Storage
              </h4>

              <div class="space-y-3 text-xs">
                <div class="p-3.5 rounded-lg bg-charcoal-800 border border-charcoal-500 space-y-2">
                  <div class="flex items-center justify-between">
                    <span class="font-bold text-charcoal-100">NVENC GPU Acceleration</span>
                    <span class="px-2.5 py-1 rounded-md text-[10px] font-bold ${
                      health.gpu_acceleration
                        ? 'bg-status-success/15 text-status-success border border-status-success/30'
                        : 'bg-charcoal-700 text-charcoal-300 border border-charcoal-500'
                    }">
                      ${health.gpu_acceleration ? 'NVIDIA NVENC ACTIVE' : 'CPU FALLBACK (x264)'}
                    </span>
                  </div>
                  <p class="text-[10px] text-charcoal-200 leading-relaxed">
                    ${health.gpu_acceleration
                      ? 'Hardware video encoder detected. Assembly rendering operates at maximum velocity.'
                      : 'Software libx264 encoder active with multi-threaded rendering.'}
                  </p>
                </div>

                <div class="p-3.5 rounded-lg bg-charcoal-800 border border-charcoal-500 space-y-2">
                  <div class="flex items-center justify-between">
                    <span class="font-bold text-charcoal-100">Available Video Storage</span>
                    <span class="font-mono text-status-success font-bold">${health.disk_free_gb} GB Free</span>
                  </div>
                  <p class="text-[10px] text-charcoal-200">
                    Temporary clips are automatically purged after final MP4 compilation.
                  </p>
                </div>

                <div class="p-3.5 rounded-lg bg-charcoal-800 border border-charcoal-500 space-y-2">
                  <div class="flex items-center justify-between">
                    <span class="font-bold text-charcoal-100">Database Engine</span>
                    <span class="font-mono text-lime-primary font-bold">SQLite 3 (WAL Mode)</span>
                  </div>
                  <p class="text-[10px] text-charcoal-200">
                    Write-Ahead Logging enables concurrent non-blocking readers and thread-safe writes.
                  </p>
                </div>
              </div>
            </div>
          </div>
        `}
      </div>
    </div>
  `;
}
