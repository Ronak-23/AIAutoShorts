/**
 * ui/src/components/Navbar.js
 * ===========================
 * Top navigation header with channel selector, system status, and user profile.
 * Redesigned with Charcoal & Electric Lime design system.
 */

import { html } from '../html.js';
import { Icon } from './Icons.js';
import { useAuth } from '../context/AuthContext.js';
import { usePipeline } from '../context/PipelineContext.js';

export function Navbar({ onOpenCreateRun, onToggleMobileMenu }) {
  const { user, logout } = useAuth();
  const { channels, activeChannel, setActiveChannel } = usePipeline();

  return html`
    <header class="h-16 border-b border-charcoal-500 bg-charcoal-800 px-3 sm:px-6 flex items-center justify-between sticky top-0 z-20">
      <div class="flex items-center space-x-2 sm:space-x-3 min-w-0">
        <!-- Mobile Drawer Toggle Button -->
        <button
          onClick=${onToggleMobileMenu}
          class="lg:hidden p-2 text-charcoal-300 hover:text-charcoal-100 rounded-lg hover:bg-charcoal-700 transition shrink-0"
          title="Open Navigation Menu"
        >
          <${Icon} name="menu" className="w-5 h-5" />
        </button>

        <!-- Logo & Technical Branding -->
        <div class="flex items-center space-x-2.5 shrink-0">
          <div class="w-8 h-8 sm:w-9 sm:h-9 rounded-lg bg-charcoal-700 border border-charcoal-500 flex items-center justify-center text-lime-primary">
            <${Icon} name="video" className="w-4 h-4 sm:w-5 sm:h-5 text-lime-primary" />
          </div>
          <div>
            <h1 class="text-sm sm:text-base font-bold tracking-tight text-charcoal-100">
              AIAutoShorts
            </h1>
            <span class="hidden sm:block text-[10px] uppercase font-semibold tracking-wider text-lime-primary -mt-0.5">
              Autonomous Studio
            </span>
          </div>
        </div>

        <div class="hidden sm:block h-5 w-px bg-charcoal-500 mx-1 sm:mx-2 shrink-0"></div>

        <!-- Active Channel Dropdown -->
        ${channels && channels.length > 0 && html`
          <div class="flex items-center space-x-1 sm:space-x-2 min-w-0">
            <span class="hidden md:inline text-xs text-charcoal-200 font-medium shrink-0">Channel:</span>
            <select
              value=${activeChannel ? activeChannel.id : ""}
              onChange=${(e) => {
                const found = channels.find((c) => c.id === e.target.value);
                if (found) setActiveChannel(found);
              }}
              class="bg-charcoal-700 border border-charcoal-500 text-xs font-semibold rounded-lg px-2 sm:px-3 py-1.5 text-charcoal-100 focus:outline-none focus:border-lime-primary focus:ring-1 focus:ring-lime-primary transition max-w-[120px] sm:max-w-[170px] md:max-w-xs truncate"
            >
              ${channels.map((c) => html`
                <option key=${c.id} value=${c.id}>
                  ${c.display_name} (${c.name})
                </option>
              `)}
            </select>
          </div>
        `}
      </div>

      <!-- Right controls -->
      <div class="flex items-center space-x-2 sm:space-x-3 shrink-0">
        <!-- Create New Short Button (Primary Electric Lime) -->
        <button
          onClick=${onOpenCreateRun}
          class="flex items-center space-x-1 sm:space-x-2 px-3 sm:px-4 py-1.5 rounded-lg bg-lime-primary hover:bg-lime-secondary text-charcoal-900 text-xs font-bold transition active:scale-95 shrink-0"
        >
          <${Icon} name="sparkles" className="w-4 h-4" />
          <span class="hidden xs:inline">New Short</span>
        </button>

        <!-- User Profile Pill -->
        ${user && html`
          <div class="flex items-center space-x-2 sm:space-x-3 pl-2 sm:pl-3 border-l border-charcoal-500 shrink-0">
            <div class="flex items-center space-x-1.5 sm:space-x-2">
              <div class="w-7 h-7 rounded-lg bg-charcoal-600 text-lime-primary text-xs font-bold flex items-center justify-center border border-charcoal-500 shrink-0">
                ${user.username[0].toUpperCase()}
              </div>
              <span class="hidden md:inline text-xs font-medium text-charcoal-200 truncate max-w-[90px]">${user.username}</span>
            </div>
            <button
              onClick=${logout}
              title="Sign Out"
              class="p-1.5 text-charcoal-300 hover:text-status-error rounded-lg hover:bg-charcoal-700 transition"
            >
              <${Icon} name="logout" className="w-4 h-4" />
            </button>
          </div>
        `}
      </div>
    </header>
  `;
}
