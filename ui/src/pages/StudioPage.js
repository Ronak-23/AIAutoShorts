/**
 * ui/src/pages/StudioPage.js
 * ==========================
 * Real-time production studio: LangGraph topology visualizer, live SSE terminal, and run inspector.
 * Redesigned with Charcoal & Electric Lime design system.
 */

import { html, useState } from '../html.js';
import { Icon } from '../components/Icons.js';
import { usePipeline } from '../context/PipelineContext.js';
import { WorkflowGraph } from '../components/WorkflowGraph.js';
import { LiveConsole } from '../components/LiveConsole.js';
import { api, authStorage } from '../api/client.js';

function getFilename(filepath) {
  if (!filepath) return '';
  const parts = String(filepath).replace(/\\/g, '/').split('/');
  return parts[parts.length - 1] || '';
}

export function StudioPage({ onOpenCreateRun, onOpenHITL, onOpenVideo }) {
  const { runs, activeRun, selectRun, refreshRuns, showToast } = usePipeline();
  const [selectedNode, setSelectedNode] = useState(null);

  const handleCancel = async () => {
    if (!activeRun) return;
    try {
      await api.pipeline.cancelRun(activeRun.run_id);
      showToast("Pipeline run cancelled.", "info");
      await refreshRuns();
    } catch (err) {
      showToast(`Cancel failed: ${err.message}`, "error");
    }
  };

  const videoFilename = activeRun && activeRun.final_video_path ? getFilename(activeRun.final_video_path) : '';

  return html`
    <div class="p-4 sm:p-6 lg:p-8 space-y-6 sm:space-y-8 max-w-7xl mx-auto w-full">
      <!-- Top Run Selector & Action Header -->
      <div class="bg-charcoal-800 border border-charcoal-500 rounded-xl p-4 sm:p-5 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
        <div class="flex items-center space-x-4 w-full lg:w-auto min-w-0">
          <div class="space-y-1 w-full min-w-0">
            <span class="text-[10px] font-bold uppercase tracking-wider text-charcoal-300">
              Active Production Job
            </span>
            <div class="flex items-center space-x-3 w-full min-w-0">
              <select
                value=${activeRun ? activeRun.run_id : ""}
                onChange=${(e) => selectRun(e.target.value)}
                class="bg-charcoal-700 border border-charcoal-500 text-xs sm:text-sm font-semibold rounded-lg px-3 sm:px-4 py-2 text-charcoal-100 focus:outline-none focus:border-lime-primary focus:ring-1 focus:ring-lime-primary w-full max-w-full lg:max-w-md truncate"
              >
                ${(runs || []).map((r) => html`
                  <option key=${r.run_id} value=${r.run_id}>
                    ${r.channel_display_name || r.channel_name} — ${r.story_title || r.run_id} (${r.status})
                  </option>
                `)}
                ${(!runs || runs.length === 0) && html`
                  <option value="">No production runs yet</option>
                `}
              </select>
            </div>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2 sm:gap-3 w-full lg:w-auto">
          ${activeRun && activeRun.status === 'paused_for_approval' && html`
            <button
              onClick=${() => onOpenHITL && onOpenHITL(activeRun)}
              class="px-3.5 sm:px-4 py-2 rounded-lg bg-status-warning hover:brightness-110 text-charcoal-900 text-xs font-bold flex items-center space-x-2 transition active:scale-95"
            >
              <${Icon} name="clock" className="w-4 h-4" />
              <span>Review Script & Assets</span>
            </button>
          `}

          ${activeRun && videoFilename && html`
            <button
              onClick=${() => {
                const token = authStorage.getToken();
                const streamUrl = `/api/media/video/${videoFilename}${token ? `?token=${token}` : ''}`;
                onOpenVideo && onOpenVideo({
                  stream_url: streamUrl,
                  filename: videoFilename,
                  title: activeRun.story_title || activeRun.run_id,
                  channel_name: activeRun.channel_name,
                  qc_score: activeRun.qc_score,
                  duration_seconds: activeRun.video_duration || 55
                });
              }}
              class="px-3.5 sm:px-4 py-2 rounded-lg bg-status-success hover:brightness-110 text-charcoal-900 text-xs font-bold flex items-center space-x-2 transition"
            >
              <${Icon} name="play" className="w-4 h-4" />
              <span>Watch Short</span>
            </button>
          `}

          ${activeRun && (activeRun.status === 'running' || activeRun.status === 'paused_for_approval') && html`
            <button
              onClick=${handleCancel}
              class="px-3.5 sm:px-4 py-2 rounded-lg bg-charcoal-700 hover:bg-status-error/20 text-status-error border border-status-error/30 text-xs font-semibold transition"
            >
              Cancel Run
            </button>
          `}

          <button
            onClick=${onOpenCreateRun}
            class="px-3.5 sm:px-4 py-2 rounded-lg bg-lime-primary hover:bg-lime-secondary text-charcoal-900 text-xs font-bold flex items-center space-x-2 transition active:scale-95"
          >
            <${Icon} name="plus" className="w-4 h-4" />
            <span>New Production</span>
          </button>
        </div>
      </div>

      <!-- Active Run Progress Bar Card -->
      ${activeRun && html`
        <div class="p-4 sm:p-5 rounded-xl bg-charcoal-700 border border-charcoal-500 space-y-3">
          <div class="flex flex-wrap items-center justify-between gap-2 text-xs">
            <div class="flex items-center space-x-3">
              <span class="px-2.5 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider ${
                activeRun.status === 'completed'
                  ? 'bg-status-success/15 text-status-success border border-status-success/30'
                  : activeRun.status === 'running'
                  ? 'bg-lime-primary/15 text-lime-primary border border-lime-primary/30'
                  : activeRun.status === 'paused_for_approval'
                  ? 'bg-status-warning/15 text-status-warning border border-status-warning/30'
                  : 'bg-status-error/15 text-status-error border border-status-error/30'
              }">
                ${activeRun.status}
              </span>
              <span class="text-charcoal-200 font-semibold">
                Current Node: <span class="text-lime-primary font-mono">${activeRun.current_node || 'N/A'}</span>
              </span>
            </div>
            <span class="text-lime-primary font-mono font-bold">${activeRun.progress_percentage}% Completed</span>
          </div>

          <div class="w-full bg-charcoal-900 border border-charcoal-500 h-2.5 rounded-full overflow-hidden">
            <div
              class="bg-lime-primary h-full transition-all duration-500 rounded-full"
              style=${{ width: `${activeRun.progress_percentage}%` }}
            />
          </div>

          ${activeRun.error && html`
            <div class="p-3 rounded-lg bg-status-error/10 border border-status-error/30 text-status-error text-xs flex items-start space-x-2">
              <${Icon} name="alert-circle" className="w-4 h-4 text-status-error shrink-0 mt-0.5" />
              <div>
                <span class="font-bold">Execution Error: </span>
                <span>${activeRun.error}</span>
              </div>
            </div>
          `}
        </div>
      `}

      <!-- LangGraph Visualizer -->
      <${WorkflowGraph}
        activeRun=${activeRun}
        selectedNode=${selectedNode}
        onSelectNode=${setSelectedNode}
      />

      <!-- Lower Split: Output Inspector & Live Event Terminal -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Live Run Inspector -->
        <div class="bg-charcoal-700 border border-charcoal-500 rounded-xl p-4 sm:p-6 space-y-4">
          <h3 class="text-xs font-bold uppercase tracking-wider text-charcoal-200 flex items-center space-x-2">
            <${Icon} name="layers" className="w-4 h-4 text-lime-primary" />
            <span>Artifact & Script Inspector</span>
          </h3>

          ${!activeRun ? html`
            <div class="text-xs text-charcoal-300 p-8 text-center">No active run selected.</div>
          ` : html`
            <div class="space-y-4 text-xs">
              <div class="space-y-1">
                <span class="text-[10px] text-charcoal-300 uppercase font-bold">Story Headline</span>
                <div class="text-sm font-bold text-charcoal-100 leading-snug">
                  ${activeRun.story_title || activeRun.custom_topic || 'Pending discovery...'}
                </div>
              </div>

              ${activeRun.full_script && html`
                <div class="space-y-1">
                  <span class="text-[10px] text-charcoal-300 uppercase font-bold">Full Narration Script</span>
                  <div class="p-3.5 rounded-lg bg-charcoal-800 border border-charcoal-500 text-charcoal-100 font-mono text-xs italic leading-relaxed max-h-48 overflow-y-auto">
                    "${activeRun.full_script}"
                  </div>
                </div>
              `}

              <div class="grid grid-cols-2 gap-3">
                <div class="p-3 rounded-lg bg-charcoal-800 border border-charcoal-500">
                  <span class="text-[10px] text-charcoal-300 uppercase font-semibold">QC Score</span>
                  <div class="text-base font-bold text-status-success">
                    ${activeRun.qc_score ? `${activeRun.qc_score}/100` : 'Pending'}
                  </div>
                </div>
                <div class="p-3 rounded-lg bg-charcoal-800 border border-charcoal-500">
                  <span class="text-[10px] text-charcoal-300 uppercase font-semibold">Video QC Review</span>
                  <div class="text-base font-bold text-charcoal-100">
                    ${activeRun.video_qc_score ? `${activeRun.video_qc_score}/100` : 'Pending'}
                  </div>
                </div>
              </div>
            </div>
          `}
        </div>

        <!-- Live Streaming Terminal -->
        <${LiveConsole} runId=${activeRun ? activeRun.run_id : null} />
      </div>
    </div>
  `;
}
