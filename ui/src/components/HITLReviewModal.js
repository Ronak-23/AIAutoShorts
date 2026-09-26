/**
 * ui/src/components/HITLReviewModal.js
 * ===================================
 * Human-in-the-Loop review drawer allowing creators to inspect generated scripts,
 * scenes, and audio before publishing.
 * Redesigned with Charcoal & Electric Lime design system.
 */

import { html, useState } from '../html.js';
import { Icon } from './Icons.js';
import { api } from '../api/client.js';
import { usePipeline } from '../context/PipelineContext.js';

export function HITLReviewModal({ isOpen, onClose, run }) {
  if (!isOpen || !run) return null;

  const { refreshRuns, showToast } = usePipeline();
  const [feedback, setFeedback] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleDecision = async (approved) => {
    setIsSubmitting(true);
    try {
      await api.pipeline.approveHITL(run.run_id, approved, feedback);
      showToast(approved ? "Short approved! Publishing..." : "Short rejected.", approved ? "success" : "info");
      await refreshRuns();
      onClose();
    } catch (err) {
      showToast(`Review action failed: ${err.message}`, "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  return html`
    <div class="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-3 sm:p-4 overflow-y-auto">
      <div class="bg-charcoal-800 border border-status-warning/40 rounded-xl p-5 sm:p-6 max-w-2xl w-full shadow-xl space-y-5 my-auto max-h-[92vh] overflow-y-auto">
        <!-- Header -->
        <div class="flex items-center justify-between border-b border-charcoal-500 pb-4">
          <div class="flex items-center space-x-3">
            <div class="p-2.5 rounded-lg bg-status-warning/15 text-status-warning border border-status-warning/30">
              <${Icon} name="clock" className="w-5 h-5" />
            </div>
            <div>
              <span class="text-[10px] font-bold uppercase tracking-wider text-status-warning">
                Human-in-the-Loop Checkpoint
              </span>
              <h3 class="text-base font-bold text-charcoal-100 leading-snug">
                Review Before Publishing: ${run.story_title || run.script_title || run.run_id}
              </h3>
            </div>
          </div>
          <button onClick=${onClose} class="text-charcoal-300 hover:text-charcoal-100 p-1 rounded-lg">
            <${Icon} name="close" className="w-5 h-5" />
          </button>
        </div>

        <!-- Content Details -->
        <div class="space-y-4 text-xs">
          <!-- Script Preview -->
          <div class="p-4 rounded-xl bg-charcoal-700 border border-charcoal-500 space-y-2">
            <div class="flex items-center justify-between text-charcoal-200 font-semibold text-[11px]">
              <span>Narration Script</span>
              <span class="font-mono">${run.full_script ? run.full_script.split(/\s+/).length : 0} words</span>
            </div>
            <p class="text-charcoal-100 text-xs leading-relaxed italic bg-charcoal-800 p-3.5 rounded-lg border border-charcoal-500 font-mono">
              "${run.full_script || 'Script unavailable.'}"
            </p>
          </div>

          <!-- Quality Scores -->
          <div class="grid grid-cols-2 gap-3">
            <div class="p-3 rounded-lg bg-charcoal-700 border border-charcoal-500">
              <span class="text-[10px] uppercase font-bold text-charcoal-300">Creative QC Score</span>
              <div class="text-base font-bold text-status-success mt-0.5">
                ${run.qc_score ? `${run.qc_score}/100` : 'Passed'}
              </div>
              <p class="text-[10px] text-charcoal-300 mt-1">${run.qc_feedback || 'Hook and pacing approved.'}</p>
            </div>
            <div class="p-3 rounded-lg bg-charcoal-700 border border-charcoal-500">
              <span class="text-[10px] uppercase font-bold text-charcoal-300">Target Channel</span>
              <div class="text-base font-bold text-lime-primary mt-0.5">${run.channel_display_name || run.channel_name}</div>
              <p class="text-[10px] text-charcoal-300 mt-1">1080x1920 60fps vertical format</p>
            </div>
          </div>

          <!-- Feedback text area (if rejecting) -->
          <div class="space-y-1">
            <label class="text-[11px] font-semibold text-charcoal-200">
              Revision / Feedback Notes (Optional)
            </label>
            <textarea
              rows="2"
              placeholder="e.g. Make the hook punchier, reduce background music volume..."
              value=${feedback}
              onChange=${(e) => setFeedback(e.target.value)}
              class="w-full bg-charcoal-700 border border-charcoal-500 text-xs rounded-lg p-3 text-charcoal-100 placeholder-charcoal-300 focus:outline-none focus:border-lime-primary focus:ring-1 focus:ring-lime-primary transition"
            />
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-4 border-t border-charcoal-500">
          <button
            onClick=${() => handleDecision(false)}
            disabled=${isSubmitting}
            class="w-full sm:w-auto px-4 py-2 rounded-lg bg-status-error/15 hover:bg-status-error/25 text-status-error border border-status-error/30 text-xs font-semibold transition flex items-center justify-center space-x-2"
          >
            <${Icon} name="close" className="w-4 h-4" />
            <span>Reject Draft</span>
          </button>

          <div class="flex items-center justify-end space-x-3 w-full sm:w-auto">
            <button
              onClick=${onClose}
              class="px-4 py-2 text-xs font-semibold text-charcoal-300 hover:text-charcoal-100 transition"
            >
              Cancel
            </button>
            <button
              onClick=${() => handleDecision(true)}
              disabled=${isSubmitting}
              class="flex-1 sm:flex-initial px-5 py-2.5 rounded-lg bg-status-success hover:brightness-110 text-charcoal-900 text-xs font-bold flex items-center justify-center space-x-2 transition active:scale-95 disabled:opacity-50"
            >
              <${Icon} name="check" className="w-4 h-4" />
              <span>Approve & Publish Short</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  `;
}
