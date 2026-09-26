/**
 * ui/src/pages/ChannelsPage.js
 * ============================
 * Multi-tenant channel management: Create, configure, test voiceover, and manage channel DNA.
 * Redesigned with Charcoal & Electric Lime design system.
 */

import { html, useState, useEffect } from '../html.js';
import { Icon } from '../components/Icons.js';
import { usePipeline } from '../context/PipelineContext.js';
import { api } from '../api/client.js';

export function ChannelsPage({ onOpenCreateChannel, onEditChannel }) {
  const { channels, refreshChannels, showToast } = usePipeline();
  const [testingVoiceId, setTestingVoiceId] = useState(null);
  const [connectingChannelId, setConnectingChannelId] = useState(null);

  useEffect(() => {
    const handleAuthMessage = (event) => {
      if (event.data && event.data.type === 'YOUTUBE_AUTH_SUCCESS') {
        showToast(`YouTube channel "${event.data.channelTitle || 'Channel'}" connected successfully!`, "success");
        refreshChannels();
      } else if (event.data && event.data.type === 'YOUTUBE_AUTH_ERROR') {
        showToast(`YouTube connection failed: ${event.data.error || 'Unknown error'}`, "error");
      }
    };
    window.addEventListener("message", handleAuthMessage);
    return () => window.removeEventListener("message", handleAuthMessage);
  }, []);

  const handleConnectYouTube = async (chan) => {
    setConnectingChannelId(chan.id);
    try {
      const res = await api.channels.getYouTubeAuthUrl(chan.id);
      if (!res.configured) {
        showToast(res.message || "YouTube credentials not configured in .env", "error");
        return;
      }
      if (res.auth_url) {
        const width = 600;
        const height = 700;
        const left = window.screen.width / 2 - width / 2;
        const top = window.screen.height / 2 - height / 2;
        window.open(
          res.auth_url,
          "YouTubeAuthPopup",
          `width=${width},height=${height},top=${top},left=${left},status=no,resizable=yes`
        );
      }
    } catch (err) {
      showToast(`Failed to initialize YouTube auth: ${err.message}`, "error");
    } finally {
      setConnectingChannelId(null);
    }
  };

  const handleDisconnectYouTube = async (chan) => {
    if (!confirm(`Are you sure you want to disconnect YouTube publishing for "${chan.display_name}"?`)) return;
    try {
      await api.channels.disconnectYouTube(chan.id);
      showToast("YouTube disconnected.", "info");
      refreshChannels();
    } catch (err) {
      showToast(`Failed to disconnect: ${err.message}`, "error");
    }
  };

  const handleTestVoice = async (chan) => {
    setTestingVoiceId(chan.id);
    try {
      const audioBlob = await api.channels.testVoice(
        chan.voice_name,
        chan.voice_rate,
        `This is ${chan.display_name}. Video production ready.`
      );
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      audio.play();
    } catch (err) {
      showToast(`Voice test failed: ${err.message}`, "error");
    } finally {
      setTestingVoiceId(null);
    }
  };

  const handleDelete = async (chan) => {
    if (!confirm(`Are you sure you want to delete channel "${chan.display_name}"?`)) return;
    try {
      await api.channels.delete(chan.id);
      showToast("Channel deleted successfully", "info");
      refreshChannels();
    } catch (err) {
      showToast(`Delete failed: ${err.message}`, "error");
    }
  };

  return html`
    <div class="p-4 sm:p-6 lg:p-8 space-y-6 sm:space-y-8 max-w-7xl mx-auto w-full">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 class="text-xl font-bold text-charcoal-100 flex items-center space-x-2">
            <${Icon} name="users" className="w-5 h-5 text-lime-primary" />
            <span>Multi-Tenant Channel Profiles</span>
          </h2>
          <p class="text-xs text-charcoal-200 mt-1">
            Configure isolated channel personalities, viral niches, neural voices, and visual branding.
          </p>
        </div>

        <button
          onClick=${onOpenCreateChannel}
          class="w-full sm:w-auto px-4 py-2.5 rounded-lg bg-lime-primary hover:bg-lime-secondary text-charcoal-900 text-xs font-bold flex items-center justify-center space-x-2 transition active:scale-95"
        >
          <${Icon} name="plus" className="w-4 h-4" />
          <span>Add Channel</span>
        </button>
      </div>

      <!-- Channels Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
        ${channels.map((chan) => html`
          <div
            key=${chan.id}
            class="bg-charcoal-700 border border-charcoal-500 rounded-xl p-5 sm:p-6 flex flex-col justify-between hover:border-lime-primary/40 transition space-y-4"
          >
            <div class="space-y-4">
              <div class="flex items-start justify-between">
                <div class="flex items-center space-x-3">
                  <div class="w-10 h-10 rounded-lg bg-charcoal-600 border border-charcoal-500 flex items-center justify-center text-lime-primary font-bold text-sm">
                    ${chan.display_name[0].toUpperCase()}
                  </div>
                  <div>
                    <h3 class="text-sm font-bold text-charcoal-100">${chan.display_name}</h3>
                    <span class="text-[10px] font-mono text-charcoal-300">${chan.name}</span>
                  </div>
                </div>

                <div class="flex items-center space-x-1">
                  <button
                    onClick=${() => onEditChannel(chan)}
                    class="p-1.5 text-charcoal-300 hover:text-charcoal-100 rounded-lg hover:bg-charcoal-600 transition"
                    title="Edit Channel"
                  >
                    <${Icon} name="settings" className="w-4 h-4" />
                  </button>
                  <button
                    onClick=${() => handleDelete(chan)}
                    class="p-1.5 text-charcoal-300 hover:text-status-error rounded-lg hover:bg-charcoal-600 transition"
                    title="Delete Channel"
                  >
                    <${Icon} name="trash" className="w-4 h-4" />
                  </button>
                </div>
              </div>

              <div class="space-y-2 text-xs">
                <div class="p-3 rounded-lg bg-charcoal-800 border border-charcoal-500 space-y-1">
                  <span class="text-[10px] font-bold uppercase text-charcoal-300">Niche</span>
                  <p class="text-charcoal-100 font-medium line-clamp-2">${chan.niche}</p>
                </div>
                <div class="p-3 rounded-lg bg-charcoal-800 border border-charcoal-500 space-y-1">
                  <span class="text-[10px] font-bold uppercase text-charcoal-300">Tone & Pace</span>
                  <p class="text-charcoal-100 font-medium line-clamp-2">${chan.tone}</p>
                </div>
              </div>

              <!-- Voice & Subtitles Info -->
              <div class="p-3 rounded-lg bg-charcoal-800 border border-charcoal-500 space-y-2">
                <div class="flex items-center justify-between text-xs">
                  <span class="text-charcoal-300 text-[10px] font-bold uppercase">Voice Talent</span>
                  <button
                    onClick=${() => handleTestVoice(chan)}
                    disabled=${testingVoiceId === chan.id}
                    class="text-lime-primary hover:text-lime-secondary text-[11px] font-semibold flex items-center space-x-1"
                  >
                    <${Icon} name=${testingVoiceId === chan.id ? 'refresh' : 'volume'} className="w-3.5 h-3.5 ${testingVoiceId === chan.id ? 'animate-spin' : ''}" />
                    <span>${testingVoiceId === chan.id ? 'Playing...' : 'Test Audio'}</span>
                  </button>
                </div>
                <div class="text-charcoal-100 font-medium text-xs">
                  ${chan.voice_name.replace('en-US-', '').replace('Neural', '')} (${chan.voice_rate})
                </div>
                <div class="flex justify-between text-[11px] text-charcoal-300 pt-1 border-t border-charcoal-500 font-mono">
                  <span>BGM: ${chan.default_bgm_mood}</span>
                  <span>Captions: ${chan.caption_style}</span>
                </div>
              </div>

              <!-- YouTube Publishing Integration -->
              <div class="p-3 rounded-lg bg-charcoal-800 border border-charcoal-500 flex items-center justify-between">
                <div class="flex items-center space-x-2.5">
                  <div class="w-7 h-7 rounded-lg ${chan.has_youtube_auth ? 'bg-status-success/15 text-status-success border border-status-success/30' : 'bg-charcoal-700 text-charcoal-300 border border-charcoal-500'} flex items-center justify-center">
                    <${Icon} name="video" className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <span class="text-[10px] font-bold uppercase text-charcoal-300 block">YouTube Publishing</span>
                    <span class="text-xs font-semibold ${chan.has_youtube_auth ? 'text-status-success' : 'text-charcoal-300'}">
                      ${chan.has_youtube_auth ? `✓ ${chan.youtube_channel_title || 'Authorized'}` : 'Not Linked'}
                    </span>
                  </div>
                </div>
                ${chan.has_youtube_auth ? html`
                  <button
                    onClick=${() => handleDisconnectYouTube(chan)}
                    class="px-2.5 py-1 text-[10px] font-semibold text-charcoal-300 hover:text-status-error rounded-md border border-charcoal-500 hover:border-status-error/30 transition"
                    title="Disconnect YouTube Channel"
                  >
                    Disconnect
                  </button>
                ` : html`
                  <button
                    onClick=${() => handleConnectYouTube(chan)}
                    disabled=${connectingChannelId === chan.id}
                    class="px-3 py-1.5 rounded-lg bg-charcoal-700 hover:bg-charcoal-600 text-status-error border border-status-error/30 text-xs font-semibold transition flex items-center space-x-1.5"
                  >
                    <${Icon} name=${connectingChannelId === chan.id ? 'refresh' : 'external-link'} className="w-3.5 h-3.5 ${connectingChannelId === chan.id ? 'animate-spin' : ''}" />
                    <span>${connectingChannelId === chan.id ? 'Connecting...' : 'Connect YT'}</span>
                  </button>
                `}
              </div>
            </div>

            <div class="pt-3 border-t border-charcoal-500 flex items-center justify-between text-[11px] text-charcoal-300 font-mono">
              <span>Duration: <strong class="text-charcoal-200">${chan.video_duration_seconds}s</strong></span>
              <span>Framerate: <strong class="text-charcoal-200">${chan.fps} fps</strong></span>
            </div>
          </div>
        `)}
      </div>
    </div>
  `;
}
