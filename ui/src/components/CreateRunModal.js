/**
 * ui/src/components/CreateRunModal.js
 * ===================================
 * Modal dialog for launching autonomous YouTube Short generation jobs.
 * Redesigned with Charcoal & Electric Lime design system.
 */

import { html, useState } from '../html.js';
import { Icon } from './Icons.js';
import { usePipeline } from '../context/PipelineContext.js';

export function CreateRunModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  const { channels, activeChannel, startNewRun } = usePipeline();

  const [channelName, setChannelName] = useState(activeChannel ? activeChannel.name : (channels[0] ? channels[0].name : "demo_channel"));
  const [topicMode, setTopicMode] = useState("auto"); // "auto" | "custom"
  const [customTopic, setCustomTopic] = useState("");
  const [autoPost, setAutoPost] = useState(false);
  const [interruptBeforePublish, setInterruptBeforePublish] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await startNewRun({
        channel_name: channelName,
        custom_topic: topicMode === "custom" && customTopic.trim() ? customTopic.trim() : null,
        auto_post_youtube: autoPost,
        interrupt_before_publish: interruptBeforePublish
      });
      onClose();
    } catch (err) {
      // Toast already handled by context
    } finally {
      setIsSubmitting(false);
    }
  };

  return html`
    <div class="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-3 sm:p-4 overflow-y-auto">
      <div class="bg-charcoal-800 border border-charcoal-500 rounded-xl p-5 sm:p-6 max-w-lg w-full shadow-xl space-y-5 max-h-[92vh] overflow-y-auto my-auto">
        <div class="flex items-center justify-between border-b border-charcoal-500 pb-4">
          <div class="flex items-center space-x-2.5">
            <div class="p-2 rounded-lg bg-lime-primary/10 text-lime-primary border border-lime-primary/25">
              <${Icon} name="sparkles" className="w-5 h-5" />
            </div>
            <div>
              <h3 class="text-base font-bold text-charcoal-100">Generate Viral Short</h3>
              <p class="text-xs text-charcoal-200">Launch autonomous multi-agent video production</p>
            </div>
          </div>
          <button onClick=${onClose} class="text-charcoal-300 hover:text-charcoal-100 p-1 rounded-lg">
            <${Icon} name="close" className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit=${handleSubmit} class="space-y-4">
          <!-- Channel Selector -->
          <div class="space-y-1.5">
            <label class="text-xs font-semibold text-charcoal-200">Target Channel Profile</label>
            <select
              value=${channelName}
              onChange=${(e) => setChannelName(e.target.value)}
              class="w-full bg-charcoal-700 border border-charcoal-500 text-xs rounded-lg p-2.5 text-charcoal-100 focus:outline-none focus:border-lime-primary focus:ring-1 focus:ring-lime-primary transition"
            >
              ${channels.map((c) => html`
                <option key=${c.id} value=${c.name}>
                  ${c.display_name} (${c.name}) — ${c.niche.slice(0, 35)}...
                </option>
              `)}
            </select>
          </div>

          <!-- Topic Source Toggle -->
          <div class="space-y-2">
            <label class="text-xs font-semibold text-charcoal-200">Story & Topic Source</label>
            <div class="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick=${() => setTopicMode("auto")}
                class="p-3 rounded-lg border text-xs font-semibold text-left transition ${
                  topicMode === 'auto'
                    ? 'bg-lime-primary/10 border-lime-primary text-charcoal-100'
                    : 'bg-charcoal-700 border-charcoal-500 text-charcoal-200 hover:bg-charcoal-600'
                }"
              >
                <div class="flex items-center space-x-2">
                  <${Icon} name="activity" className="w-4 h-4 text-lime-primary" />
                  <span>Auto-Trend Scout</span>
                </div>
                <div class="text-[10px] text-charcoal-300 font-normal mt-1">
                  Curates top trending story via RSS & Google Trends.
                </div>
              </button>

              <button
                type="button"
                onClick=${() => setTopicMode("custom")}
                class="p-3 rounded-lg border text-xs font-semibold text-left transition ${
                  topicMode === 'custom'
                    ? 'bg-lime-primary/10 border-lime-primary text-charcoal-100'
                    : 'bg-charcoal-700 border-charcoal-500 text-charcoal-200 hover:bg-charcoal-600'
                }"
              >
                <div class="flex items-center space-x-2">
                  <${Icon} name="sparkles" className="w-4 h-4 text-lime-primary" />
                  <span>Custom Prompt</span>
                </div>
                <div class="text-[10px] text-charcoal-300 font-normal mt-1">
                  Direct topic or breakthrough hook idea.
                </div>
              </button>
            </div>

            ${topicMode === 'custom' && html`
              <textarea
                rows="3"
                placeholder="e.g. Why quantum computers might break Bitcoin cryptography by 2028..."
                value=${customTopic}
                onChange=${(e) => setCustomTopic(e.target.value)}
                class="w-full bg-charcoal-700 border border-charcoal-500 text-xs rounded-lg p-3 text-charcoal-100 placeholder-charcoal-300 focus:outline-none focus:border-lime-primary focus:ring-1 focus:ring-lime-primary transition mt-2"
                required
              />
            `}
          </div>

          <!-- Checkbox Options -->
          <div class="space-y-2.5 pt-2 border-t border-charcoal-500">
            <label class="flex items-center space-x-3 text-xs text-charcoal-200 cursor-pointer">
              <input
                type="checkbox"
                checked=${interruptBeforePublish}
                onChange=${(e) => setInterruptBeforePublish(e.target.checked)}
                class="w-4 h-4 rounded bg-charcoal-700 border-charcoal-500 accent-lime-primary"
              />
              <div>
                <span class="font-semibold text-charcoal-100">Pause for Human Review (Recommended)</span>
                <span class="text-[11px] text-charcoal-300 block">Preview script, scenes, and audio before publishing</span>
              </div>
            </label>

            <label class="flex items-center space-x-3 text-xs text-charcoal-200 cursor-pointer">
              <input
                type="checkbox"
                checked=${autoPost}
                onChange=${(e) => setAutoPost(e.target.checked)}
                class="w-4 h-4 rounded bg-charcoal-700 border-charcoal-500 accent-lime-primary"
              />
              <div>
                <span class="font-semibold text-charcoal-100">Auto-Upload to YouTube</span>
                <span class="text-[11px] block ${
                  (channels.find(c => c.name === channelName) || activeChannel)?.has_youtube_auth 
                    ? 'text-status-success font-medium' 
                    : 'text-charcoal-300'
                }">
                  ${
                    (channels.find(c => c.name === channelName) || activeChannel)?.has_youtube_auth
                      ? `✓ Authorized to publish to ${(channels.find(c => c.name === channelName) || activeChannel)?.youtube_channel_title || 'YouTube Channel'}`
                      : 'Requires YouTube authorization (connect in Channels tab)'
                  }
                </span>
              </div>
            </label>
          </div>

          <!-- Buttons -->
          <div class="flex items-center justify-end space-x-3 pt-4 border-t border-charcoal-500">
            <button
              type="button"
              onClick=${onClose}
              class="px-4 py-2 text-xs font-semibold text-charcoal-300 hover:text-charcoal-100 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled=${isSubmitting}
              class="px-5 py-2.5 rounded-lg bg-lime-primary hover:bg-lime-secondary text-charcoal-900 text-xs font-bold flex items-center space-x-2 transition active:scale-95 disabled:opacity-50"
            >
              <${Icon} name=${isSubmitting ? 'refresh' : 'play'} className="w-4 h-4 ${isSubmitting ? 'animate-spin' : ''}" />
              <span>${isSubmitting ? 'Starting...' : 'Launch Production'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  `;
}
