/**
 * ui/src/App.js
 * =============
 * Main application layout, view routing, modal dispatching, and notification toasts.
 * Redesigned with Charcoal & Electric Lime design system.
 */

import { html, useState } from './html.js';
import { useAuth } from './context/AuthContext.js';
import { usePipeline } from './context/PipelineContext.js';
import { Navbar } from './components/Navbar.js';
import { Sidebar } from './components/Sidebar.js';
import { CreateRunModal } from './components/CreateRunModal.js';
import { ChannelModal } from './components/ChannelModal.js';
import { HITLReviewModal } from './components/HITLReviewModal.js';
import { ScheduleModal } from './components/ScheduleModal.js';
import { ShortsVideoPlayer } from './components/ShortsVideoPlayer.js';
import { DashboardPage } from './pages/DashboardPage.js';
import { StudioPage } from './pages/StudioPage.js';
import { ChannelsPage } from './pages/ChannelsPage.js';
import { GalleryPage } from './pages/GalleryPage.js';
import { SchedulesPage } from './pages/SchedulesPage.js';
import { AnalyticsPage } from './pages/AnalyticsPage.js';
import { SettingsPage } from './pages/SettingsPage.js';
import { LoginPage } from './pages/LoginPage.js';
import { ErrorBoundary } from './components/ErrorBoundary.js';
import { Icon } from './components/Icons.js';

export function App() {
  const { user, loading } = useAuth();
  const { toast } = usePipeline();

  const [currentTab, setTab] = useState('dashboard');
  const [isMobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isCreateRunOpen, setCreateRunOpen] = useState(false);
  const [isChannelModalOpen, setChannelModalOpen] = useState(false);
  const [editingChannel, setEditingChannel] = useState(null);
  const [isHITLOpen, setHITLOpen] = useState(false);
  const [hitlRun, setHitlRun] = useState(null);
  const [isScheduleOpen, setScheduleOpen] = useState(false);
  const [activeVideo, setActiveVideo] = useState(null);

  if (loading) {
    return html`
      <div class="min-h-screen bg-charcoal-900 flex items-center justify-center text-charcoal-200 text-xs">
        <div class="flex items-center space-x-2">
          <${Icon} name="refresh" className="w-5 h-5 animate-spin text-lime-primary" />
          <span>Loading AIAutoShorts Studio...</span>
        </div>
      </div>
    `;
  }

  if (!user) {
    return html`<${LoginPage} />`;
  }

  const renderContent = () => {
    switch (currentTab) {
      case 'dashboard':
        return html`<${DashboardPage}
          setTab=${setTab}
          onOpenCreateRun=${() => setCreateRunOpen(true)}
          onOpenVideo=${(vid) => setActiveVideo(vid)}
        />`;
      case 'studio':
        return html`<${StudioPage}
          onOpenCreateRun=${() => setCreateRunOpen(true)}
          onOpenHITL=${(run) => { setHitlRun(run); setHITLOpen(true); }}
          onOpenVideo=${(vid) => setActiveVideo(vid)}
        />`;
      case 'channels':
        return html`<${ChannelsPage}
          onOpenCreateChannel=${() => { setEditingChannel(null); setChannelModalOpen(true); }}
          onEditChannel=${(chan) => { setEditingChannel(chan); setChannelModalOpen(true); }}
        />`;
      case 'gallery':
        return html`<${GalleryPage} onOpenVideo=${(vid) => setActiveVideo(vid)} />`;
      case 'schedules':
        return html`<${SchedulesPage} onOpenCreateSchedule=${() => setScheduleOpen(true)} />`;
      case 'analytics':
        return html`<${AnalyticsPage} />`;
      case 'settings':
        return html`<${SettingsPage} />`;
      default:
        return html`<${DashboardPage} setTab=${setTab} onOpenCreateRun=${() => setCreateRunOpen(true)} />`;
    }
  };

  const mobileNavItems = [
    { id: 'dashboard', label: 'Home', icon: 'layers' },
    { id: 'studio', label: 'Studio', icon: 'activity' },
    { id: 'channels', label: 'Channels', icon: 'users' },
    { id: 'gallery', label: 'Gallery', icon: 'video' },
  ];

  return html`
    <div class="min-h-screen bg-charcoal-900 text-charcoal-100 flex flex-col selection:bg-lime-primary selection:text-charcoal-900">
      <!-- Navbar -->
      <${Navbar}
        onOpenCreateRun=${() => setCreateRunOpen(true)}
        onToggleMobileMenu=${() => setMobileMenuOpen(!isMobileMenuOpen)}
      />

      <!-- Main Layout Body -->
      <div class="flex-1 flex overflow-hidden relative">
        <!-- Sidebar (Desktop aside & Mobile drawer) -->
        <${Sidebar}
          currentTab=${currentTab}
          setTab=${setTab}
          isOpen=${isMobileMenuOpen}
          onClose=${() => setMobileMenuOpen(false)}
        />

        <!-- Scrollable Page Container -->
        <main class="flex-1 overflow-y-auto bg-charcoal-900 pb-16 lg:pb-0">
          <${ErrorBoundary}>
            ${renderContent()}
          </${ErrorBoundary}>
        </main>
      </div>

      <!-- Mobile Bottom Navigation Bar -->
      <nav class="lg:hidden h-14 bg-charcoal-800/95 border-t border-charcoal-500 backdrop-blur flex items-center justify-around px-2 z-30 shrink-0">
        ${mobileNavItems.map((item) => {
          const isActive = currentTab === item.id;
          return html`
            <button
              key=${item.id}
              onClick=${() => setTab(item.id)}
              class="flex flex-col items-center justify-center flex-1 py-1 px-2 text-[10px] font-medium transition rounded-md ${
                isActive ? 'text-lime-primary bg-lime-primary/10 font-bold' : 'text-charcoal-300 hover:text-charcoal-100'
              }"
            >
              <${Icon} name=${item.icon} className="w-5 h-5 mb-0.5 ${isActive ? 'text-lime-primary' : 'text-charcoal-300'}" />
              <span>${item.label}</span>
            </button>
          `;
        })}
        <!-- Menu/More Button on Mobile Bottom Nav -->
        <button
          onClick=${() => setMobileMenuOpen(true)}
          class="flex flex-col items-center justify-center flex-1 py-1 px-2 text-[10px] font-medium text-charcoal-300 hover:text-charcoal-100 transition rounded-md"
        >
          <${Icon} name="menu" className="w-5 h-5 mb-0.5 text-charcoal-300" />
          <span>More</span>
        </button>
      </nav>

      <!-- Modals -->
      <${CreateRunModal}
        isOpen=${isCreateRunOpen}
        onClose=${() => setCreateRunOpen(false)}
      />

      <${ChannelModal}
        isOpen=${isChannelModalOpen}
        onClose=${() => { setChannelModalOpen(false); setEditingChannel(null); }}
        channel=${editingChannel}
      />

      <${HITLReviewModal}
        isOpen=${isHITLOpen}
        onClose=${() => { setHITLOpen(false); setHitlRun(null); }}
        run=${hitlRun}
      />

      <${ScheduleModal}
        isOpen=${isScheduleOpen}
        onClose=${() => setScheduleOpen(false)}
      />

      <${ShortsVideoPlayer}
        video=${activeVideo}
        onClose=${() => setActiveVideo(null)}
      />

      <!-- Toast Notification Alert -->
      ${toast && html`
        <div class="fixed bottom-16 lg:bottom-6 right-4 left-4 sm:left-auto sm:right-6 max-w-sm z-50 flex items-center space-x-2 px-4 py-3 rounded-xl shadow-lg border text-xs font-semibold backdrop-blur-md ${
          toast.type === 'error'
            ? 'bg-charcoal-700 text-status-error border-status-error/40'
            : toast.type === 'success'
            ? 'bg-charcoal-700 text-status-success border-status-success/40'
            : 'bg-charcoal-700 text-lime-primary border-lime-primary/40'
        }">
          <${Icon} name=${toast.type === 'error' ? 'alert-circle' : toast.type === 'success' ? 'check-circle' : 'activity'} className="w-4 h-4 shrink-0" />
          <span class="truncate">${toast.message}</span>
        </div>
      `}
    </div>
  `;
}
