/**
 * ui/src/components/ShortsVideoPlayer.js
 * =====================================
 * Vertical 9:16 video player modal with custom playback controls and metadata.
 * Redesigned with Charcoal & Electric Lime design system.
 */

import { html, useState, useRef } from '../html.js';
import { Icon } from './Icons.js';
import { authStorage, api } from '../api/client.js';

export function ShortsVideoPlayer({ video, onClose }) {
  if (!video) return null;

  const token = authStorage.getToken();
  const effectiveStreamUrl = video.stream_url && !video.stream_url.includes("token=") && token
    ? `${video.stream_url}${video.stream_url.includes("?") ? "&" : "?"}token=${token}`
    : (video.stream_url || "");

  const videoRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(true);
  const [progress, setProgress] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [youtubeVideoId, setYoutubeVideoId] = useState(video.youtube_video_id || null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);

  const handleUploadToYouTube = async () => {
    if (!video.run_id) return;
    setIsUploading(true);
    setUploadError(null);
    try {
      const res = await api.media.uploadToYouTube(video.run_id);
      if (res.success && res.youtube_video_id) {
        setYoutubeVideoId(res.youtube_video_id);
        video.youtube_video_id = res.youtube_video_id;
      }
    } catch (err) {
      setUploadError(err.message || "Failed to upload to YouTube");
    } finally {
      setIsUploading(false);
    }
  };

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (videoRef.current.paused) {
      videoRef.current.play();
      setIsPlaying(true);
    } else {
      videoRef.current.pause();
      setIsPlaying(false);
    }
  };

  const handleTimeUpdate = () => {
    if (!videoRef.current) return;
    const cur = videoRef.current.currentTime;
    const dur = videoRef.current.duration || 1;
    setCurrentTime(cur);
    setProgress((cur / dur) * 100);
  };

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration);
    }
  };

  const handleSeek = (e) => {
    if (!videoRef.current) return;
    const seekTime = (e.target.value / 100) * duration;
    videoRef.current.currentTime = seekTime;
    setProgress(e.target.value);
  };

  return html`
    <div class="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-3 sm:p-4 overflow-y-auto">
      <div class="bg-charcoal-800 border border-charcoal-500 rounded-xl overflow-hidden max-w-2xl w-full flex flex-col md:flex-row shadow-xl max-h-[92vh] my-auto">
        <!-- 9:16 Video Container -->
        <div class="relative w-full md:w-[300px] lg:w-[320px] max-h-[45vh] md:max-h-none aspect-[9/16] bg-black shrink-0 flex items-center justify-center overflow-hidden mx-auto">
          <video
            ref=${videoRef}
            src=${effectiveStreamUrl}
            class="w-full h-full object-contain md:object-cover"
            autoPlay
            loop
            playsInline
            onTimeUpdate=${handleTimeUpdate}
            onLoadedMetadata=${handleLoadedMetadata}
            onClick=${togglePlay}
          />

          <!-- Play/Pause Overlay Button -->
          <button
            onClick=${togglePlay}
            class="absolute inset-0 m-auto w-14 h-14 rounded-full bg-black/60 text-lime-primary flex items-center justify-center backdrop-blur transition ${
              isPlaying ? 'opacity-0 hover:opacity-100' : 'opacity-100'
            }"
          >
            <${Icon} name=${isPlaying ? 'pause' : 'play'} className="w-6 h-6 ml-0.5" />
          </button>

          <!-- Scrub Bar -->
          <div class="absolute bottom-0 inset-x-0 p-3 bg-gradient-to-t from-black/90 to-transparent">
            <input
              type="range"
              min="0"
              max="100"
              value=${progress}
              onChange=${handleSeek}
              class="w-full h-1 bg-charcoal-600 rounded-lg appearance-none cursor-pointer accent-lime-primary"
            />
            <div class="flex justify-between text-[10px] text-charcoal-200 font-mono mt-1">
              <span>${currentTime.toFixed(1)}s</span>
              <span>${duration.toFixed(1)}s</span>
            </div>
          </div>
        </div>

        <!-- Video Metadata & Actions Panel -->
        <div class="flex-1 p-4 sm:p-6 flex flex-col justify-between overflow-y-auto min-h-0 bg-charcoal-800">
          <div class="space-y-4">
            <div class="flex items-start justify-between">
              <div>
                <span class="text-[10px] font-bold uppercase tracking-wider text-lime-primary">
                  ${video.channel_name || 'Short'}
                </span>
                <h3 class="text-base font-bold text-charcoal-100 mt-0.5 leading-snug">
                  ${video.title || video.filename}
                </h3>
              </div>
              <button
                onClick=${onClose}
                class="p-1.5 text-charcoal-300 hover:text-charcoal-100 rounded-lg hover:bg-charcoal-700 transition"
              >
                <${Icon} name="close" className="w-5 h-5" />
              </button>
            </div>

            <div class="grid grid-cols-2 gap-3 text-xs">
              <div class="p-3 rounded-lg bg-charcoal-700 border border-charcoal-500">
                <span class="text-charcoal-300 text-[10px] uppercase font-semibold">QC Score</span>
                <div class="text-base font-bold text-status-success mt-0.5">
                  ${video.qc_score ? `${video.qc_score}/100` : 'Approved'}
                </div>
              </div>
              <div class="p-3 rounded-lg bg-charcoal-700 border border-charcoal-500">
                <span class="text-charcoal-300 text-[10px] uppercase font-semibold">File Size</span>
                <div class="text-base font-bold text-charcoal-100 mt-0.5 font-mono">
                  ${video.file_size_mb || 'N/A'} MB
                </div>
              </div>
            </div>

            <div class="space-y-2 text-xs text-charcoal-200">
              <div class="flex justify-between py-1 border-b border-charcoal-500">
                <span>Resolution</span>
                <span class="font-mono text-charcoal-100">1080 x 1920 (Vertical)</span>
              </div>
              <div class="flex justify-between py-1 border-b border-charcoal-500">
                <span>Framerate</span>
                <span class="font-mono text-charcoal-100">60 FPS</span>
              </div>
              <div class="flex justify-between items-center py-1.5 border-b border-charcoal-500">
                <span>YouTube Status</span>
                ${youtubeVideoId ? html`
                  <a
                    href="https://youtube.com/shorts/${youtubeVideoId}"
                    target="_blank"
                    class="text-status-error hover:underline font-semibold flex items-center space-x-1"
                  >
                    <span>Watch Online</span>
                    <${Icon} name="external-link" className="w-3.5 h-3.5" />
                  </a>
                ` : html`
                  <button
                    onClick=${handleUploadToYouTube}
                    disabled=${isUploading}
                    class="px-2.5 py-1 rounded-lg bg-charcoal-700 hover:bg-charcoal-600 text-status-error border border-status-error/30 text-[11px] font-bold flex items-center space-x-1.5 transition disabled:opacity-50"
                  >
                    <${Icon} name=${isUploading ? 'refresh' : 'video'} className="w-3 h-3 ${isUploading ? 'animate-spin' : ''}" />
                    <span>${isUploading ? 'Uploading...' : 'Publish to YT'}</span>
                  </button>
                `}
              </div>
              ${uploadError && html`
                <div class="p-2 rounded-lg bg-status-error/10 border border-status-error/30 text-status-error text-[11px] mt-1">
                  ${uploadError}
                </div>
              `}
            </div>
          </div>

          <!-- Bottom Action Buttons -->
          <div class="pt-6 border-t border-charcoal-500 flex items-center space-x-3">
            <a
              href=${effectiveStreamUrl}
              download=${video.filename}
              class="flex-1 py-2 rounded-lg bg-charcoal-700 hover:bg-charcoal-600 text-charcoal-100 text-xs font-semibold text-center flex items-center justify-center space-x-2 border border-charcoal-500 transition"
            >
              <${Icon} name="download" className="w-4 h-4" />
              <span>Download MP4</span>
            </a>
            ${!youtubeVideoId ? html`
              <button
                onClick=${handleUploadToYouTube}
                disabled=${isUploading}
                class="flex-1 py-2 rounded-lg bg-charcoal-700 hover:bg-status-error/20 text-status-error border border-status-error/30 text-xs font-semibold text-center flex items-center justify-center space-x-2 transition disabled:opacity-50"
              >
                <${Icon} name=${isUploading ? 'refresh' : 'video'} className="w-4 h-4 ${isUploading ? 'animate-spin' : ''}" />
                <span>${isUploading ? 'Uploading...' : 'Upload to YouTube'}</span>
              </button>
            ` : html`
              <a
                href="https://youtube.com/shorts/${youtubeVideoId}"
                target="_blank"
                class="flex-1 py-2 rounded-lg bg-charcoal-700 hover:bg-status-error/20 text-status-error border border-status-error/30 text-xs font-semibold text-center flex items-center justify-center space-x-2 transition"
              >
                <${Icon} name="external-link" className="w-4 h-4" />
                <span>Watch on YouTube</span>
              </a>
            `}
            <button
              onClick=${() => {
                navigator.clipboard.writeText(window.location.origin + effectiveStreamUrl);
                alert("Direct video URL copied to clipboard!");
              }}
              class="px-3.5 py-2 rounded-lg bg-charcoal-700 hover:bg-charcoal-600 text-charcoal-200 text-xs font-semibold border border-charcoal-500 transition"
            >
              Copy Link
            </button>
          </div>
        </div>
      </div>
    </div>
  `;
}
