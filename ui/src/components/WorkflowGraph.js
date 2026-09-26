/**
 * ui/src/components/WorkflowGraph.js
 * ==================================
 * Interactive visual representation of the 12-stage LangGraph multi-agent pipeline.
 * Redesigned with Charcoal & Electric Lime design system.
 */

import { html } from '../html.js';
import { Icon } from './Icons.js';

export function WorkflowGraph({ activeRun, onSelectNode, selectedNode }) {
  const completed = (activeRun && activeRun.completed_nodes) || [];
  const currentNode = activeRun && activeRun.current_node;
  const status = activeRun && activeRun.status;

  const getNodeStatus = (nodeId) => {
    if (!activeRun) return 'pending';
    if (currentNode === nodeId) {
      if (status === 'paused_for_approval') return 'paused';
      if (status === 'failed') return 'failed';
      if (status === 'completed') return 'completed';
      return 'running';
    }
    if (completed.includes(nodeId)) return 'completed';
    return 'pending';
  };

  const stages = [
    {
      group: "1. Ideation & Planning",
      nodes: [
        { id: "init_pipeline", label: "Preflight Check", desc: "A/B Recipe & Context", icon: "shield" },
        { id: "scout_trend", label: "Trend Discovery", desc: "RSS & Google Trends", icon: "activity" },
        { id: "scriptwriter", label: "Scriptwriter", desc: "Hook, SSML & Scenes", icon: "sparkles" },
        { id: "legal_check", label: "Legal Check", desc: "Compliance & Safety", icon: "shield" },
        { id: "quality_control", label: "QC Reviewer", desc: "Viral Gatekeeper", icon: "check-circle" },
      ]
    },
    {
      group: "2. Parallel Media Asset Production",
      nodes: [
        { id: "voiceover", label: "Neural Voiceover", desc: "EdgeTTS + Whisper ASS", icon: "volume" },
        { id: "visual_curator", label: "Visual Curator", desc: "Pexels B-Roll + CLIP", icon: "video" },
        { id: "music_director", label: "Music Director", desc: "Dynamic BGM Scoring", icon: "zap" },
        { id: "thumbnail", label: "AI Thumbnail", desc: "High-CTR Graphic", icon: "sparkles" },
      ]
    },
    {
      group: "3. Assembly & Publishing",
      nodes: [
        { id: "assemble_video", label: "FFmpeg Assembler", desc: "Ducking & Vertical Crop", icon: "layers" },
        { id: "video_qc", label: "AI Video QC", desc: "Gemini Visual Review", icon: "eye" },
        { id: "publish_youtube", label: "YouTube Publish", desc: "Auto-Post & Archive", icon: "external-link" },
      ]
    }
  ];

  return html`
    <div class="bg-charcoal-700 border border-charcoal-500 rounded-xl p-4 sm:p-6 space-y-4 sm:space-y-6">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 class="text-sm font-bold text-charcoal-100 flex items-center space-x-2">
            <${Icon} name="activity" className="w-4 h-4 text-lime-primary" />
            <span>Multi-Agent LangGraph Topology</span>
          </h2>
          <p class="text-xs text-charcoal-200 mt-0.5">
            Cyclic review loop, parallel asset fan-out, and Human-in-the-Loop checkpoints.
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-3 text-xs">
          <span class="flex items-center space-x-1 text-status-success font-medium">
            <span class="w-2 h-2 rounded-full bg-status-success"></span>
            <span>Completed</span>
          </span>
          <span class="flex items-center space-x-1 text-lime-primary font-medium">
            <span class="w-2 h-2 rounded-full bg-lime-primary"></span>
            <span>Running</span>
          </span>
          <span class="flex items-center space-x-1 text-charcoal-300 font-medium">
            <span class="w-2 h-2 rounded-full bg-charcoal-500"></span>
            <span>Pending</span>
          </span>
        </div>
      </div>

      <!-- Stage Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
        ${stages.map((stage) => html`
          <div class="bg-charcoal-800 border border-charcoal-500 rounded-lg p-4 space-y-3">
            <div class="text-[11px] font-bold tracking-wider text-charcoal-200 uppercase border-b border-charcoal-500 pb-2">
              ${stage.group}
            </div>
            <div class="space-y-2.5">
              ${stage.nodes.map((node) => {
                const nodeStatus = getNodeStatus(node.id);
                const isSelected = selectedNode === node.id;

                let statusBadge = html`<span class="w-2 h-2 rounded-full bg-charcoal-500"></span>`;
                let borderStyle = "border-charcoal-500 bg-charcoal-700/50 text-charcoal-200";

                if (nodeStatus === 'completed') {
                  statusBadge = html`<${Icon} name="check-circle" className="w-4 h-4 text-status-success" />`;
                  borderStyle = "border-status-success/40 bg-status-success/10 text-charcoal-100";
                } else if (nodeStatus === 'running') {
                  statusBadge = html`<span class="w-2.5 h-2.5 rounded-full bg-lime-primary"></span>`;
                  borderStyle = "border-lime-primary bg-lime-primary/10 text-charcoal-100 node-running";
                } else if (nodeStatus === 'paused') {
                  statusBadge = html`<${Icon} name="clock" className="w-4 h-4 text-status-warning" />`;
                  borderStyle = "border-status-warning/60 bg-status-warning/15 text-status-warning";
                } else if (nodeStatus === 'failed') {
                  statusBadge = html`<${Icon} name="alert-circle" className="w-4 h-4 text-status-error" />`;
                  borderStyle = "border-status-error/60 bg-status-error/15 text-status-error";
                }

                return html`
                  <div
                    key=${node.id}
                    onClick=${() => onSelectNode && onSelectNode(node.id)}
                    class="p-3 rounded-lg border transition cursor-pointer flex items-center justify-between ${borderStyle} ${
                      isSelected ? 'ring-2 ring-lime-primary' : 'hover:border-charcoal-400'
                    }"
                  >
                    <div class="flex items-center space-x-3">
                      <div class="p-2 rounded-md bg-charcoal-600 text-charcoal-100">
                        <${Icon} name=${node.icon} className="w-4 h-4" />
                      </div>
                      <div>
                        <div class="text-xs font-bold leading-none">${node.label}</div>
                        <div class="text-[10px] text-charcoal-300 mt-1">${node.desc}</div>
                      </div>
                    </div>
                    <div>${statusBadge}</div>
                  </div>
                `;
              })}
            </div>
          </div>
        `)}
      </div>
    </div>
  `;
}
