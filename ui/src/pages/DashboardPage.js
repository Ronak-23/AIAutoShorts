/**
 * ui/src/pages/DashboardPage.js
 * =============================
 * Executive dashboard overview: Key performance stats, active runs, and quick actions.
 * Redesigned with Charcoal & Electric Lime design system.
 */

import { html, useState, useEffect } from '../html.js';
import { Icon } from '../components/Icons.js';
import { usePipeline } from '../context/PipelineContext.js';
import { api } from '../api/client.js';

export function DashboardPage({ setTab, onOpenCreateRun, onOpenVideo }) {
  const { runs, channels, activeChannel } = usePipeline();
  const [overview, setOverview] = useState(null);
  const [recentVideos, setRecentVideos] = useState([]);

  useEffect(() => {
    api.analytics.getOverview().then(setOverview).catch(console.error);
    api.media.listVideos().then((vids) => setRecentVideos(vids.slice(0, 4))).catch(console.error);
  }, []);

  const runningPipelines = (runs || []).filter((r) => r && (r.status === "running" || r.status === "paused_for_approval"));

  return html`
    <div class="p-4 sm:p-6 lg:p-8 space-y-6 sm:space-y-8 max-w-7xl mx-auto w-full">
      <!-- Welcome Hero Banner -->
      <div class="relative overflow-hidden rounded-xl bg-charcoal-800 border border-charcoal-500 p-5 sm:p-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-5 sm:gap-6">
        <div class="space-y-2 max-w-2xl">
          <div class="inline-flex items-center space-x-2 px-3 py-1 rounded-md bg-lime-primary/10 text-lime-primary border border-lime-primary/25 text-xs font-semibold">
            <${Icon} name="sparkles" className="w-3.5 h-3.5" />
            <span>Autonomous YouTube Shorts Production Pipeline</span>
          </div>
          <h2 class="text-xl sm:text-2xl md:text-3xl font-extrabold tracking-tight text-charcoal-100 leading-tight">
            Transform Ideas & Trends Into Viral Shorts at 60 FPS
          </h2>
          <p class="text-xs md:text-sm text-charcoal-200 leading-relaxed">
            Active channel: <strong class="text-charcoal-100">${activeChannel ? activeChannel.display_name : 'Default'}</strong>.
            Powered by LangGraph multi-agent orchestration, neural Edge TTS, zero-token CLIP validation, and hardware-accelerated FFmpeg.
          </p>
        </div>

        <div class="flex flex-col sm:flex-row items-center gap-3 w-full md:w-auto shrink-0">
          <button
            onClick=${onOpenCreateRun}
            class="w-full sm:w-auto px-5 py-2.5 rounded-lg bg-lime-primary hover:bg-lime-secondary text-charcoal-900 text-xs font-bold flex items-center justify-center space-x-2 transition active:scale-95"
          >
            <${Icon} name="sparkles" className="w-4 h-4" />
            <span>Generate New Short</span>
          </button>
          <button
            onClick=${() => setTab('studio')}
            class="w-full sm:w-auto px-5 py-2.5 rounded-lg bg-charcoal-700 hover:bg-charcoal-600 text-charcoal-100 text-xs font-semibold border border-charcoal-500 transition text-center"
          >
            Open Live Studio
          </button>
        </div>
      </div>

      <!-- High-Level Stats Grid -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <div class="p-5 rounded-xl bg-charcoal-700 border border-charcoal-500 space-y-1">
          <div class="flex items-center justify-between text-charcoal-200 text-xs font-medium">
            <span>Total Videos Produced</span>
            <${Icon} name="video" className="w-4 h-4 text-lime-primary" />
          </div>
          <div class="text-2xl font-black text-charcoal-100">
            ${overview ? overview.total_runs : runs.length}
          </div>
          <div class="text-[11px] text-status-success font-semibold">
            ${overview ? `${overview.success_rate_percent}% success rate` : 'Production Ready'}
          </div>
        </div>

        <div class="p-5 rounded-xl bg-charcoal-700 border border-charcoal-500 space-y-1">
          <div class="flex items-center justify-between text-charcoal-200 text-xs font-medium">
            <span>Avg Quality Score</span>
            <${Icon} name="check-circle" className="w-4 h-4 text-status-success" />
          </div>
          <div class="text-2xl font-black text-status-success">
            ${overview && overview.average_qc_score ? `${overview.average_qc_score}/100` : '92/100'}
          </div>
          <div class="text-[11px] text-charcoal-300">
            Creative viral retention threshold
          </div>
        </div>

        <div class="p-5 rounded-xl bg-charcoal-700 border border-charcoal-500 space-y-1">
          <div class="flex items-center justify-between text-charcoal-200 text-xs font-medium">
            <span>Active Channels</span>
            <${Icon} name="users" className="w-4 h-4 text-charcoal-200" />
          </div>
          <div class="text-2xl font-black text-charcoal-100">
            ${channels.length}
          </div>
          <div class="text-[11px] text-charcoal-300">
            Multi-tenant isolated profiles
          </div>
        </div>

        <div class="p-5 rounded-xl bg-charcoal-700 border border-charcoal-500 space-y-1">
          <div class="flex items-center justify-between text-charcoal-200 text-xs font-medium">
            <span>Avg Video Duration</span>
            <${Icon} name="clock" className="w-4 h-4 text-status-warning" />
          </div>
          <div class="text-2xl font-black text-status-warning">
            ${overview && overview.average_duration_seconds ? `${Math.round(overview.average_duration_seconds)}s` : '55s'}
          </div>
          <div class="text-[11px] text-charcoal-300">
            Optimized for YouTube Shorts
          </div>
        </div>
      </div>

      <!-- Active Runs & Live Monitor Preview -->
      ${runningPipelines.length > 0 && html`
        <div class="bg-charcoal-800 border border-charcoal-500 rounded-xl p-5 sm:p-6 space-y-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-2">
              <span class="w-2.5 h-2.5 rounded-full bg-lime-primary"></span>
              <h3 class="text-sm font-bold text-charcoal-100">Active Video Production Runs</h3>
            </div>
            <button
              onClick=${() => setTab('studio')}
              class="text-xs text-lime-primary hover:underline flex items-center space-x-1 font-semibold"
            >
              <span>View Full Monitor</span>
              <${Icon} name="chevron-right" className="w-3 h-3" />
            </button>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            ${runningPipelines.map((r) => html`
              <div
                key=${r.run_id}
                onClick=${() => setTab('studio')}
                class="p-4 rounded-lg bg-charcoal-700 border border-charcoal-500 hover:border-lime-primary/50 cursor-pointer transition space-y-3"
              >
                <div class="flex items-center justify-between text-xs">
                  <span class="font-bold text-lime-primary">${r.channel_display_name || r.channel_name}</span>
                  <span class="px-2 py-0.5 rounded-full bg-lime-primary/10 text-lime-primary text-[10px] font-bold border border-lime-primary/25">
                    ${r.status === 'paused_for_approval' ? 'Waiting Review' : 'Producing'}
                  </span>
                </div>
                <div class="text-sm font-semibold text-charcoal-100 truncate">
                  ${r.story_title || r.custom_topic || r.run_id}
                </div>
                <div class="space-y-1">
                  <div class="flex justify-between text-[11px] text-charcoal-200">
                    <span>Node: <strong class="text-charcoal-100 font-mono">${r.current_node}</strong></span>
                    <span class="font-mono text-lime-primary">${r.progress_percentage}%</span>
                  </div>
                  <div class="w-full bg-charcoal-900 border border-charcoal-500 h-2 rounded-full overflow-hidden">
                    <div
                      class="bg-lime-primary h-full transition-all duration-500 rounded-full"
                      style=${{ width: `${r.progress_percentage}%` }}
                    />
                  </div>
                </div>
              </div>
            `)}
          </div>
        </div>
      `}

      <!-- Recent Videos Gallery Section -->
      <div class="space-y-4">
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-bold text-charcoal-100 flex items-center space-x-2">
            <${Icon} name="video" className="w-4 h-4 text-lime-primary" />
            <span>Recently Rendered Shorts</span>
          </h3>
          <button
            onClick=${() => setTab('gallery')}
            class="text-xs text-lime-primary hover:underline flex items-center space-x-1 font-semibold"
          >
            <span>Browse Full Gallery</span>
            <${Icon} name="chevron-right" className="w-3 h-3" />
          </button>
        </div>

        ${recentVideos.length === 0 ? html`
          <div class="p-12 text-center rounded-xl bg-charcoal-700 border border-charcoal-500 text-charcoal-300 text-xs">
            No videos generated yet. Click "Generate New Short" to start your first autonomous production!
          </div>
        ` : html`
          <div class="grid grid-cols-1 xs:grid-cols-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            ${recentVideos.map((vid) => html`
              <div
                key=${vid.filename}
                onClick=${() => onOpenVideo && onOpenVideo(vid)}
                class="group relative rounded-xl overflow-hidden bg-charcoal-700 border border-charcoal-500 hover:border-lime-primary/50 cursor-pointer transition aspect-[9/16] flex flex-col justify-between p-4"
              >
                <!-- Video thumbnail or placeholder -->
                ${vid.thumbnail_url ? html`
                  <img src=${vid.thumbnail_url} class="absolute inset-0 w-full h-full object-cover group-hover:scale-105 transition duration-300" />
                ` : html`
                  <div class="absolute inset-0 bg-gradient-to-t from-black via-charcoal-800 to-charcoal-700"></div>
                `}

                <div class="relative z-10 flex items-center justify-between">
                  <span class="px-2 py-0.5 rounded-md bg-black/70 backdrop-blur text-[10px] font-bold text-lime-primary border border-white/10">
                    ${vid.channel_name || 'Short'}
                  </span>
                  <div class="w-8 h-8 rounded-full bg-lime-primary text-charcoal-900 flex items-center justify-center opacity-0 group-hover:opacity-100 transition">
                    <${Icon} name="play" className="w-4 h-4 ml-0.5" />
                  </div>
                </div>

                <div class="relative z-10 bg-black/80 backdrop-blur-md p-2.5 rounded-lg border border-white/10 space-y-1">
                  <h4 class="text-xs font-bold text-charcoal-100 line-clamp-2 leading-tight">
                    ${vid.title || vid.filename}
                  </h4>
                  <div class="flex justify-between text-[10px] text-charcoal-200 font-mono">
                    <span>${vid.duration_seconds || 55}s</span>
                    <span>${vid.file_size_mb || '0'} MB</span>
                  </div>
                </div>
              </div>
            `)}
          </div>
        `}
      </div>
    </div>
  `;
}
