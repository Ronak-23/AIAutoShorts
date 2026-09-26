/**
 * ui/src/components/Sidebar.js
 * ============================
 * Application navigation sidebar with badges and system status.
 * Redesigned with Charcoal & Electric Lime design system.
 */

import { html } from '../html.js';
import { Icon } from './Icons.js';
import { usePipeline } from '../context/PipelineContext.js';

export function Sidebar({ currentTab, setTab, isOpen = false, onClose = () => {} }) {
  const { runs } = usePipeline();

  const activeRunningCount = runs ? runs.filter((r) => r.status === "running" || r.status === "paused_for_approval").length : 0;

  const items = [
    { id: 'dashboard', label: 'Dashboard', icon: 'layers' },
    { id: 'studio', label: 'Studio & Live Run', icon: 'activity', badge: activeRunningCount > 0 ? activeRunningCount : null },
    { id: 'channels', label: 'Channels', icon: 'users' },
    { id: 'gallery', label: 'Media Gallery', icon: 'video' },
    { id: 'schedules', label: 'Schedules', icon: 'calendar' },
    { id: 'analytics', label: 'Analytics', icon: 'chart' },
    { id: 'settings', label: 'Settings', icon: 'settings' },
  ];

  return html`
    <!-- Mobile Slide-Out Drawer Overlay -->
    ${isOpen && html`
      <div class="fixed inset-0 z-40 lg:hidden flex">
        <!-- Backdrop -->
        <div
          onClick=${onClose}
          class="fixed inset-0 bg-black/75 backdrop-blur-sm transition-opacity"
        ></div>

        <!-- Drawer Panel -->
        <aside class="relative w-72 max-w-[82vw] bg-charcoal-900 border-r border-charcoal-500 flex flex-col justify-between p-4 shadow-xl z-50 overflow-y-auto">
          <div class="space-y-4">
            <!-- Drawer Header -->
            <div class="flex items-center justify-between px-2 pb-3 border-b border-charcoal-500">
              <div class="flex items-center space-x-2.5">
                <div class="w-8 h-8 rounded-lg bg-charcoal-700 border border-charcoal-500 flex items-center justify-center text-lime-primary">
                  <${Icon} name="video" className="w-4 h-4 text-lime-primary" />
                </div>
                <div>
                  <div class="text-sm font-bold text-charcoal-100">AIAutoShorts</div>
                  <div class="text-[10px] uppercase font-semibold tracking-wider text-lime-primary -mt-0.5">Navigation</div>
                </div>
              </div>
              <button
                onClick=${onClose}
                class="p-1.5 text-charcoal-300 hover:text-charcoal-100 rounded-lg hover:bg-charcoal-700 transition"
                title="Close Menu"
              >
                <${Icon} name="close" className="w-5 h-5" />
              </button>
            </div>

            <!-- Drawer Nav Items -->
            <div class="space-y-1">
              ${items.map((item) => {
                const isActive = currentTab === item.id;
                return html`
                  <button
                    key=${item.id}
                    onClick=${() => {
                      setTab(item.id);
                      onClose();
                    }}
                    class="w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-xs font-semibold transition ${
                      isActive
                        ? 'bg-lime-primary/10 text-charcoal-100 border border-lime-primary/30'
                        : 'text-charcoal-200 hover:text-charcoal-100 hover:bg-charcoal-700'
                    }"
                  >
                    <div class="flex items-center space-x-3">
                      <${Icon}
                        name=${item.icon}
                        className="w-4 h-4 ${isActive ? 'text-lime-primary' : 'text-charcoal-300'}"
                      />
                      <span>${item.label}</span>
                    </div>
                    ${item.badge && html`
                      <span class="px-2 py-0.5 text-[10px] font-bold rounded-full bg-lime-primary text-charcoal-900">
                        ${item.badge}
                      </span>
                    `}
                  </button>
                `;
              })}
            </div>
          </div>

          <!-- Quick status box -->
          <div class="p-3.5 rounded-xl bg-charcoal-800 border border-charcoal-500 text-[11px] space-y-2 mt-4">
            <div class="flex items-center justify-between text-charcoal-200">
              <span class="flex items-center space-x-1.5">
                <span class="w-2 h-2 rounded-full bg-status-success"></span>
                <span class="font-medium">System Online</span>
              </span>
              <span class="text-status-success font-bold">Ready</span>
            </div>
            <div class="text-charcoal-300 text-[10px] font-mono">
              1080x1920 @ 60fps Vertical Engine
            </div>
          </div>
        </aside>
      </div>
    `}

    <!-- Desktop Permanent Sidebar -->
    <aside class="hidden lg:flex w-64 border-r border-charcoal-500 bg-charcoal-900 flex-col justify-between shrink-0 p-4">
      <div class="space-y-1.5">
        <div class="px-3 py-2 text-[11px] font-bold uppercase tracking-wider text-charcoal-300">
          Navigation
        </div>
        ${items.map((item) => {
          const isActive = currentTab === item.id;
          return html`
            <button
              key=${item.id}
              onClick=${() => setTab(item.id)}
              class="w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-xs font-semibold transition ${
                isActive
                  ? 'bg-lime-primary/10 text-charcoal-100 border border-lime-primary/30'
                  : 'text-charcoal-200 hover:text-charcoal-100 hover:bg-charcoal-700'
              }"
            >
              <div class="flex items-center space-x-3">
                <${Icon}
                  name=${item.icon}
                  className="w-4 h-4 ${isActive ? 'text-lime-primary' : 'text-charcoal-300'}"
                />
                <span>${item.label}</span>
              </div>
              ${item.badge && html`
                <span class="px-2 py-0.5 text-[10px] font-bold rounded-full bg-lime-primary text-charcoal-900">
                  ${item.badge}
                </span>
              `}
            </button>
          `;
        })}
      </div>

      <!-- Quick status box -->
      <div class="p-3.5 rounded-xl bg-charcoal-800 border border-charcoal-500 text-[11px] space-y-2">
        <div class="flex items-center justify-between text-charcoal-200">
          <span class="flex items-center space-x-1.5">
            <span class="w-2 h-2 rounded-full bg-status-success"></span>
            <span class="font-medium">System Online</span>
          </span>
          <span class="text-status-success font-bold">Ready</span>
        </div>
        <div class="text-charcoal-300 text-[10px] font-mono">
          1080x1920 @ 60fps Vertical Engine
        </div>
      </div>
    </aside>
  `;
}
