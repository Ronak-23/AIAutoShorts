/**
 * ui/src/pages/LoginPage.js
 * =========================
 * Clean authentication screen for multi-tenant sign in and registration.
 * Redesigned with Charcoal & Electric Lime design system.
 */

import { html, useState } from '../html.js';
import { Icon } from '../components/Icons.js';
import { useAuth } from '../context/AuthContext.js';

export function LoginPage() {
  const { login, register } = useAuth();
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (isRegister) {
        await register(username, password, email || undefined);
      } else {
        await login(username, password);
      }
    } catch (err) {
      setError(err.message || "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return html`
    <div class="min-h-screen bg-charcoal-900 flex flex-col items-center justify-center p-3 sm:p-4 selection:bg-lime-primary selection:text-charcoal-900">
      <div class="max-w-md w-full bg-charcoal-800 border border-charcoal-500 rounded-xl p-6 sm:p-8 shadow-xl space-y-6">
        <!-- Logo & Branding -->
        <div class="text-center space-y-2">
          <div class="w-12 h-12 rounded-lg bg-charcoal-700 border border-charcoal-500 mx-auto flex items-center justify-center text-lime-primary">
            <${Icon} name="video" className="w-6 h-6 text-lime-primary" />
          </div>
          <h2 class="text-2xl font-bold text-charcoal-100 tracking-tight">AIAutoShorts</h2>
          <p class="text-xs text-charcoal-200">
            Autonomous YouTube Shorts Production Pipeline
          </p>
        </div>

        <!-- Tab Toggle -->
        <div class="grid grid-cols-2 p-1 rounded-lg bg-charcoal-700 border border-charcoal-500 text-xs font-bold">
          <button
            onClick=${() => { setIsRegister(false); setError(""); }}
            class="py-2 rounded-md transition ${!isRegister ? 'bg-lime-primary text-charcoal-900 shadow-sm' : 'text-charcoal-200 hover:text-charcoal-100'}"
          >
            Sign In
          </button>
          <button
            onClick=${() => { setIsRegister(true); setError(""); }}
            class="py-2 rounded-md transition ${isRegister ? 'bg-lime-primary text-charcoal-900 shadow-sm' : 'text-charcoal-200 hover:text-charcoal-100'}"
          >
            Register
          </button>
        </div>

        ${error && html`
          <div class="p-3 rounded-lg bg-status-error/15 border border-status-error/30 text-status-error text-xs flex items-center space-x-2">
            <${Icon} name="alert-circle" className="w-4 h-4 shrink-0" />
            <span>${error}</span>
          </div>
        `}

        <!-- Form -->
        <form onSubmit=${handleSubmit} class="space-y-4">
          <div class="space-y-1">
            <label class="text-xs font-semibold text-charcoal-200">Username</label>
            <input
              type="text"
              placeholder="e.g. creator"
              value=${username}
              onChange=${(e) => setUsername(e.target.value)}
              class="w-full bg-charcoal-700 border border-charcoal-500 text-xs rounded-lg p-2.5 text-charcoal-100 placeholder-charcoal-300 focus:outline-none focus:border-lime-primary focus:ring-1 focus:ring-lime-primary transition"
              required
            />
          </div>

          ${isRegister && html`
            <div class="space-y-1">
              <label class="text-xs font-semibold text-charcoal-200">Email Address (Optional)</label>
              <input
                type="email"
                placeholder="creator@example.com"
                value=${email}
                onChange=${(e) => setEmail(e.target.value)}
                class="w-full bg-charcoal-700 border border-charcoal-500 text-xs rounded-lg p-2.5 text-charcoal-100 placeholder-charcoal-300 focus:outline-none focus:border-lime-primary focus:ring-1 focus:ring-lime-primary transition"
              />
            </div>
          `}

          <div class="space-y-1">
            <label class="text-xs font-semibold text-charcoal-200">Password</label>
            <input
              type="password"
              placeholder="••••••••"
              value=${password}
              onChange=${(e) => setPassword(e.target.value)}
              class="w-full bg-charcoal-700 border border-charcoal-500 text-xs rounded-lg p-2.5 text-charcoal-100 placeholder-charcoal-300 focus:outline-none focus:border-lime-primary focus:ring-1 focus:ring-lime-primary transition"
              required
            />
          </div>

          <button
            type="submit"
            disabled=${loading}
            class="w-full py-2.5 rounded-lg bg-lime-primary hover:bg-lime-secondary text-charcoal-900 text-xs font-bold transition disabled:opacity-50 active:scale-95 mt-2"
          >
            <span>${loading ? 'Authenticating...' : isRegister ? 'Create Account' : 'Sign In'}</span>
          </button>
        </form>

        <div class="text-center text-[11px] text-charcoal-300 pt-3 border-t border-charcoal-500">
          Default developer login: <strong class="text-charcoal-100 font-mono">demo / demo123</strong>
        </div>
      </div>
    </div>
  `;
}
