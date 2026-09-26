/**
 * ui/src/components/ErrorBoundary.js
 * ===================================
 * React Error Boundary catching runtime rendering errors and preventing blank screen crashes.
 * Redesigned with Charcoal & Electric Lime design system.
 */

import { html, React } from '../html.js';
import { Icon } from './Icons.js';

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("[ErrorBoundary caught an error]", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return html`
        <div class="min-h-[400px] flex items-center justify-center p-8">
          <div class="max-w-md w-full bg-charcoal-800 border border-status-error/40 rounded-xl p-6 text-center space-y-4 shadow-xl">
            <div class="w-12 h-12 rounded-lg bg-status-error/15 border border-status-error/30 text-status-error flex items-center justify-center mx-auto">
              <${Icon} name="alert-circle" className="w-6 h-6" />
            </div>
            <div class="space-y-1">
              <h3 class="text-base font-bold text-charcoal-100">Something went wrong</h3>
              <p class="text-xs text-charcoal-200">
                A rendering error occurred in this view.
              </p>
            </div>
            <div class="p-3 rounded-lg bg-charcoal-900 border border-charcoal-500 text-[11px] font-mono text-status-error text-left overflow-x-auto max-h-32">
              ${this.state.error ? (this.state.error.message || String(this.state.error)) : "Unknown Error"}
            </div>
            <div class="flex items-center justify-center space-x-3 pt-2">
              <button
                onClick=${() => {
                  this.setState({ hasError: false, error: null });
                  window.location.reload();
                }}
                class="px-4 py-2 rounded-lg bg-lime-primary hover:bg-lime-secondary text-charcoal-900 text-xs font-bold transition active:scale-95"
              >
                Reload Studio
              </button>
            </div>
          </div>
        </div>
      `;
    }

    return this.props.children;
  }
}
