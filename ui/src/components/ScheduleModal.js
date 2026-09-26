/**
 * ui/src/components/ScheduleModal.js
 * ==================================
 * Modal to configure automated cron schedules for hands-free video production.
 * Redesigned with Charcoal & Electric Lime design system.
 */

import { html, useState } from '../html.js';
import { Icon } from './Icons.js';
import { api } from '../api/client.js';
import { usePipeline } from '../context/PipelineContext.js';

export function ScheduleModal({ isOpen, onClose, onCreated }) {
  if (!isOpen) return null;

  const { channels, showToast } = usePipeline();
  const [channelName, setChannelName] = useState(channels[0] ? channels[0].name : "demo_channel");
  const [frequency, setFrequency] = useState("daily");
  const [timeOfDay, setTimeOfDay] = useState("09:00");
  const [autoPost, setAutoPost] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await api.schedules.create({
        channel_name: channelName,
        frequency,
        time_of_day: timeOfDay,
        auto_post_youtube: autoPost,
        is_active: true
      });
      showToast("Automated schedule created successfully!", "success");
      if (onCreated) onCreated();
      onClose();
    } catch (err) {
      showToast(`Failed to create schedule: ${err.message}`, "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  return html`
    <div class="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-3 sm:p-4 overflow-y-auto">
      <div class="bg-charcoal-800 border border-charcoal-500 rounded-xl p-5 sm:p-6 max-w-md w-full shadow-xl space-y-5 my-auto max-h-[92vh] overflow-y-auto">
        <div class="flex items-center justify-between border-b border-charcoal-500 pb-4">
          <div class="flex items-center space-x-2.5">
            <div class="p-2 rounded-lg bg-lime-primary/10 text-lime-primary border border-lime-primary/25">
              <${Icon} name="calendar" className="w-5 h-5" />
            </div>
            <div>
              <h3 class="text-base font-bold text-charcoal-100">Create Automation Schedule</h3>
              <p class="text-xs text-charcoal-200">Autonomous recurring video production</p>
            </div>
          </div>
          <button onClick=${onClose} class="text-charcoal-300 hover:text-charcoal-100 p-1 rounded-lg">
            <${Icon} name="close" className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit=${handleSubmit} class="space-y-4">
          <div class="space-y-1.5">
            <label class="text-xs font-semibold text-charcoal-200">Target Channel</label>
            <select
              value=${channelName}
              onChange=${(e) => setChannelName(e.target.value)}
              class="w-full bg-charcoal-700 border border-charcoal-500 text-xs rounded-lg p-2.5 text-charcoal-100 focus:outline-none focus:border-lime-primary focus:ring-1 focus:ring-lime-primary transition"
            >
              ${channels.map((c) => html`
                <option key=${c.id} value=${c.name}>
                  ${c.display_name} (${c.name})
                </option>
              `)}
            </select>
          </div>

          <div class="space-y-1.5">
            <label class="text-xs font-semibold text-charcoal-200">Frequency</label>
            <select
              value=${frequency}
              onChange=${(e) => setFrequency(e.target.value)}
              class="w-full bg-charcoal-700 border border-charcoal-500 text-xs rounded-lg p-2.5 text-charcoal-100 focus:outline-none focus:border-lime-primary focus:ring-1 focus:ring-lime-primary transition"
            >
              <option value="daily">Daily (Once per day at target time)</option>
              <option value="every_12_hours">Every 12 Hours (Twice per day)</option>
              <option value="every_6_hours">Every 6 Hours (Four times per day)</option>
              <option value="hourly">Hourly (Continuous generation)</option>
            </select>
          </div>

          ${frequency === 'daily' && html`
            <div class="space-y-1.5">
              <label class="text-xs font-semibold text-charcoal-200">Target Time of Day (24h)</label>
              <input
                type="time"
                value=${timeOfDay}
                onChange=${(e) => setTimeOfDay(e.target.value)}
                class="w-full bg-charcoal-700 border border-charcoal-500 text-xs rounded-lg p-2.5 text-charcoal-100 focus:outline-none focus:border-lime-primary focus:ring-1 focus:ring-lime-primary transition"
                required
              />
            </div>
          `}

          <div class="pt-2 border-t border-charcoal-500">
            <label class="flex items-center space-x-3 text-xs text-charcoal-200 cursor-pointer">
              <input
                type="checkbox"
                checked=${autoPost}
                onChange=${(e) => setAutoPost(e.target.checked)}
                class="w-4 h-4 rounded bg-charcoal-700 border-charcoal-500 accent-lime-primary"
              />
              <span class="font-semibold text-charcoal-100">Auto-upload generated Shorts to YouTube</span>
            </label>
          </div>

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
              class="px-5 py-2.5 rounded-lg bg-lime-primary hover:bg-lime-secondary text-charcoal-900 text-xs font-bold transition active:scale-95 disabled:opacity-50"
            >
              <span>${isSubmitting ? 'Scheduling...' : 'Set Schedule'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  `;
}
