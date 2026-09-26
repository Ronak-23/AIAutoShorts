/**
 * ui/src/pages/SchedulesPage.js
 * =============================
 * Automation and cron schedules manager for hands-free autonomous production.
 * Redesigned with Charcoal & Electric Lime design system.
 */

import { html, useState, useEffect } from '../html.js';
import { Icon } from '../components/Icons.js';
import { api } from '../api/client.js';
import { usePipeline } from '../context/PipelineContext.js';

export function SchedulesPage({ onOpenCreateSchedule }) {
  const { showToast } = usePipeline();
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [triggeringId, setTriggeringId] = useState(null);

  const loadSchedules = async () => {
    setLoading(true);
    try {
      const list = await api.schedules.list();
      setSchedules(list);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSchedules();
  }, []);

  const handleTrigger = async (sched) => {
    setTriggeringId(sched.id);
    try {
      const res = await api.schedules.trigger(sched.id);
      showToast(`Automation triggered: ${res.run_id}`, "success");
      await loadSchedules();
    } catch (err) {
      showToast(`Trigger failed: ${err.message}`, "error");
    } finally {
      setTriggeringId(null);
    }
  };

  const handleDelete = async (sched) => {
    if (!confirm("Are you sure you want to delete this schedule?")) return;
    try {
      await api.schedules.delete(sched.id);
      showToast("Schedule removed", "info");
      loadSchedules();
    } catch (err) {
      showToast(`Delete failed: ${err.message}`, "error");
    }
  };

  return html`
    <div class="p-4 sm:p-6 lg:p-8 space-y-6 sm:space-y-8 max-w-7xl mx-auto w-full">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 class="text-xl font-bold text-charcoal-100 flex items-center space-x-2">
            <${Icon} name="calendar" className="w-5 h-5 text-lime-primary" />
            <span>Automated Cron Schedules</span>
          </h2>
          <p class="text-xs text-charcoal-200 mt-1">
            Hands-free autonomous video production on recurring schedules.
          </p>
        </div>

        <button
          onClick=${onOpenCreateSchedule}
          class="w-full sm:w-auto px-4 py-2.5 rounded-lg bg-lime-primary hover:bg-lime-secondary text-charcoal-900 text-xs font-bold flex items-center justify-center space-x-2 transition active:scale-95"
        >
          <${Icon} name="plus" className="w-4 h-4" />
          <span>New Schedule</span>
        </button>
      </div>

      <!-- Schedules List -->
      ${loading ? html`
        <div class="p-16 text-center text-charcoal-300 text-xs">Loading schedules...</div>
      ` : schedules.length === 0 ? html`
        <div class="p-16 text-center rounded-xl bg-charcoal-700 border border-charcoal-500 text-charcoal-300 text-xs space-y-3">
          <p>No recurring automation schedules configured yet.</p>
          <button
            onClick=${onOpenCreateSchedule}
            class="px-4 py-2 rounded-lg bg-charcoal-600 hover:bg-charcoal-500 text-charcoal-100 text-xs font-semibold border border-charcoal-500 transition"
          >
            Create Your First Schedule
          </button>
        </div>
      ` : html`
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
          ${schedules.map((sched) => html`
            <div
              key=${sched.id}
              class="bg-charcoal-700 border border-charcoal-500 rounded-xl p-5 flex flex-col justify-between hover:border-lime-primary/40 transition space-y-4"
            >
              <div class="space-y-3">
                <div class="flex items-start justify-between">
                  <div class="flex items-center space-x-3">
                    <div class="p-2.5 rounded-lg bg-lime-primary/10 text-lime-primary border border-lime-primary/25">
                      <${Icon} name="calendar" className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 class="text-sm font-bold text-charcoal-100">${sched.channel_name}</h3>
                      <span class="text-[10px] uppercase font-bold text-lime-primary">${sched.frequency}</span>
                    </div>
                  </div>
                  <button
                    onClick=${() => handleDelete(sched)}
                    class="p-1.5 text-charcoal-300 hover:text-status-error rounded-lg hover:bg-charcoal-600 transition"
                    title="Delete schedule"
                  >
                    <${Icon} name="trash" className="w-4 h-4" />
                  </button>
                </div>

                <div class="p-3 rounded-lg bg-charcoal-800 border border-charcoal-500 space-y-1.5 text-xs">
                  <div class="flex justify-between text-charcoal-200">
                    <span>Target Time</span>
                    <span class="font-mono text-charcoal-100 font-semibold">${sched.time_of_day || 'N/A'}</span>
                  </div>
                  <div class="flex justify-between text-charcoal-200">
                    <span>Auto YouTube Upload</span>
                    <span class="${sched.auto_post_youtube ? 'text-status-success font-bold' : 'text-charcoal-300'}">
                      ${sched.auto_post_youtube ? 'Enabled' : 'Disabled'}
                    </span>
                  </div>
                  <div class="flex justify-between text-charcoal-200 pt-1 border-t border-charcoal-500">
                    <span>Next Trigger</span>
                    <span class="font-mono text-lime-primary text-[11px] font-semibold">
                      ${sched.next_run_at ? new Date(sched.next_run_at).toLocaleString() : 'Pending'}
                    </span>
                  </div>
                </div>
              </div>

              <button
                onClick=${() => handleTrigger(sched)}
                disabled=${triggeringId === sched.id}
                class="w-full py-2.5 rounded-lg bg-charcoal-600 hover:bg-charcoal-500 text-charcoal-100 text-xs font-semibold flex items-center justify-center space-x-2 border border-charcoal-500 transition disabled:opacity-50"
              >
                <${Icon} name=${triggeringId === sched.id ? 'refresh' : 'play'} className="w-3.5 h-3.5 ${triggeringId === sched.id ? 'animate-spin' : ''}" />
                <span>${triggeringId === sched.id ? 'Executing...' : 'Trigger Run Now'}</span>
              </button>
            </div>
          `)}
        </div>
      `}
    </div>
  `;
}
