/**
 * ui/src/components/LiveConsole.js
 * ================================
 * Real-time SSE streaming terminal log viewer with auto-scroll and filtering.
 * Redesigned with Charcoal & Electric Lime design system.
 */

import { html, useState, useEffect, useRef } from '../html.js';
import { Icon } from './Icons.js';
import { subscribeToRunEvents } from '../api/sse.js';

export function LiveConsole({ runId }) {
  const [logs, setLogs] = useState([]);
  const [autoScroll, setAutoScroll] = useState(true);
  const [filter, setFilter] = useState('');
  const logEndRef = useRef(null);

  useEffect(() => {
    if (!runId) {
      setLogs([]);
      return;
    }

    setLogs([{
      timestamp: new Date().toLocaleTimeString(),
      type: 'info',
      message: `[AIAutoShorts] Connected to live event stream for ${runId}...`
    }]);

    const unsubscribe = subscribeToRunEvents(
      runId,
      (event) => {
        setLogs((prev) => [
          ...prev,
          {
            timestamp: new Date().toLocaleTimeString(),
            type: event.type || 'step_update',
            node: event.node || event.current_node,
            message: event.message || JSON.stringify(event)
          }
        ]);
      },
      (err) => {
        console.warn("[SSE] Event source warning", err);
      }
    );

    return () => unsubscribe();
  }, [runId]);

  useEffect(() => {
    if (autoScroll && logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  const filteredLogs = logs.filter((l) =>
    filter ? l.message.toLowerCase().includes(filter.toLowerCase()) : true
  );

  return html`
    <div class="bg-charcoal-900 border border-charcoal-500 rounded-xl overflow-hidden flex flex-col h-80">
      <!-- Terminal Header -->
      <div class="min-h-10 bg-charcoal-800 border-b border-charcoal-500 px-3 sm:px-4 py-2 sm:py-0 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
        <div class="flex items-center space-x-2 shrink-0">
          <${Icon} name="terminal" className="w-4 h-4 text-lime-primary" />
          <span class="text-xs font-mono font-bold text-charcoal-100">Live Agent Stream</span>
          <span class="text-[10px] px-2 py-0.5 rounded-md bg-charcoal-700 text-charcoal-200 border border-charcoal-500 font-mono">
            ${filteredLogs.length} events
          </span>
        </div>

        <div class="flex flex-wrap items-center gap-2 sm:space-x-3 w-full sm:w-auto">
          <!-- Filter input -->
          <input
            type="text"
            placeholder="Filter logs..."
            value=${filter}
            onChange=${(e) => setFilter(e.target.value)}
            class="bg-charcoal-900 border border-charcoal-500 text-[11px] font-mono px-2.5 py-1 rounded-md text-charcoal-100 placeholder-charcoal-300 focus:outline-none focus:border-lime-primary focus:ring-1 focus:ring-lime-primary transition flex-1 sm:flex-none w-28 sm:w-36"
          />

          <!-- Auto-scroll toggle -->
          <button
            onClick=${() => setAutoScroll(!autoScroll)}
            class="text-[11px] font-mono px-2.5 py-1 rounded-md border transition shrink-0 ${
              autoScroll
                ? 'bg-lime-primary/15 text-lime-primary border-lime-primary/30 font-semibold'
                : 'bg-charcoal-700 text-charcoal-300 border-charcoal-500'
            }"
          >
            Auto: ${autoScroll ? 'ON' : 'OFF'}
          </button>

          <!-- Clear button -->
          <button
            onClick=${() => setLogs([])}
            class="text-charcoal-300 hover:text-charcoal-100 text-xs transition p-1 shrink-0"
            title="Clear output"
          >
            <${Icon} name="trash" className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <!-- Log Terminal Body -->
      <div class="flex-1 p-4 overflow-y-auto font-mono text-[11px] space-y-1 select-text">
        ${filteredLogs.map((log, idx) => {
          let badgeColor = "text-charcoal-200";
          if (log.type === "run_started") badgeColor = "text-lime-primary font-bold";
          if (log.type === "run_completed") badgeColor = "text-status-success font-bold";
          if (log.type === "run_failed") badgeColor = "text-status-error font-bold";
          if (log.type === "node_completed") badgeColor = "text-lime-secondary font-semibold";
          if (log.type === "paused_for_approval") badgeColor = "text-status-warning font-bold";

          return html`
            <div key=${idx} class="leading-relaxed flex items-start space-x-2.5 hover:bg-charcoal-800/40 px-1 py-0.5 rounded">
              <span class="text-charcoal-300 shrink-0 select-none">${log.timestamp}</span>
              <span class="px-1.5 py-0.2 rounded bg-charcoal-800 ${badgeColor} text-[10px] shrink-0 border border-charcoal-500">
                ${log.node || log.type}
              </span>
              <span class="text-charcoal-100 break-all">${log.message}</span>
            </div>
          `;
        })}
        <div ref=${logEndRef} />
      </div>
    </div>
  `;
}
