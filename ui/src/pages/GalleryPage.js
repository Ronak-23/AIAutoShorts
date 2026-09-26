/**
 * ui/src/pages/GalleryPage.js
 * ===========================
 * Full media gallery browser with 9:16 vertical cards and direct playback modal.
 * Redesigned with Charcoal & Electric Lime design system.
 */

import { html, useState, useEffect } from '../html.js';
import { Icon } from '../components/Icons.js';
import { api } from '../api/client.js';

export function GalleryPage({ onOpenVideo }) {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  const loadVideos = async () => {
    setLoading(true);
    try {
      const data = await api.media.listVideos();
      setVideos(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadVideos();
  }, []);

  const filtered = videos.filter((v) =>
    search ? (v.title && v.title.toLowerCase().includes(search.toLowerCase())) || v.filename.toLowerCase().includes(search.toLowerCase()) : true
  );

  return html`
    <div class="p-4 sm:p-6 lg:p-8 space-y-6 sm:space-y-8 max-w-7xl mx-auto w-full">
      <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 class="text-xl font-bold text-charcoal-100 flex items-center space-x-2">
            <${Icon} name="video" className="w-5 h-5 text-lime-primary" />
            <span>Generated Shorts Gallery</span>
          </h2>
          <p class="text-xs text-charcoal-200 mt-1">
            Browse, preview, and download full 1080x1920 60fps MP4 vertical videos.
          </p>
        </div>

        <div class="flex items-center space-x-3 w-full sm:w-auto">
          <input
            type="text"
            placeholder="Search videos..."
            value=${search}
            onChange=${(e) => setSearch(e.target.value)}
            class="bg-charcoal-700 border border-charcoal-500 text-xs rounded-lg px-3.5 py-2 text-charcoal-100 placeholder-charcoal-300 focus:outline-none focus:border-lime-primary focus:ring-1 focus:ring-lime-primary transition w-full sm:w-60"
          />
          <button
            onClick=${loadVideos}
            class="p-2 rounded-lg bg-charcoal-700 border border-charcoal-500 text-charcoal-200 hover:text-charcoal-100 transition shrink-0"
            title="Refresh"
          >
            <${Icon} name="refresh" className="w-4 h-4 ${loading ? 'animate-spin' : ''}" />
          </button>
        </div>
      </div>

      <!-- Videos Grid -->
      ${loading ? html`
        <div class="p-16 text-center text-charcoal-300 text-xs">
          Loading media library...
        </div>
      ` : filtered.length === 0 ? html`
        <div class="p-16 text-center rounded-xl bg-charcoal-700 border border-charcoal-500 text-charcoal-300 text-xs space-y-2">
          <p>No rendered videos found matching your search.</p>
        </div>
      ` : html`
        <div class="grid grid-cols-1 xs:grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 sm:gap-5">
          ${filtered.map((vid) => html`
            <div
              key=${vid.filename}
              onClick=${() => onOpenVideo && onOpenVideo(vid)}
              class="group relative rounded-xl overflow-hidden bg-charcoal-700 border border-charcoal-500 hover:border-lime-primary/50 cursor-pointer transition aspect-[9/16] flex flex-col justify-between p-3.5"
            >
              ${vid.thumbnail_url ? html`
                <img src=${vid.thumbnail_url} class="absolute inset-0 w-full h-full object-cover group-hover:scale-105 transition duration-300" />
              ` : html`
                <div class="absolute inset-0 bg-gradient-to-t from-black via-charcoal-800 to-charcoal-700"></div>
              `}

              <!-- Top Badges -->
              <div class="relative z-10 flex items-center justify-between">
                <div class="flex items-center space-x-1.5">
                  <span class="px-2 py-0.5 rounded-md bg-black/70 backdrop-blur text-[10px] font-bold text-lime-primary border border-white/10">
                    ${vid.channel_name || 'Short'}
                  </span>
                  ${vid.youtube_video_id ? html`
                    <span class="px-1.5 py-0.5 rounded-md bg-status-error text-[10px] font-bold text-white shadow-sm flex items-center space-x-1" title="Published on YouTube">
                      <span>YouTube</span>
                    </span>
                  ` : ''}
                </div>
                <div class="w-8 h-8 rounded-full bg-lime-primary text-charcoal-900 flex items-center justify-center opacity-0 group-hover:opacity-100 transition">
                  <${Icon} name="play" className="w-4 h-4 ml-0.5" />
                </div>
              </div>

              <!-- Bottom Info -->
              <div class="relative z-10 bg-black/80 backdrop-blur-md p-2.5 rounded-lg border border-white/10 space-y-1">
                <h4 class="text-xs font-bold text-charcoal-100 line-clamp-2 leading-tight">
                  ${vid.title || vid.filename}
                </h4>
                <div class="flex items-center justify-between text-[10px] text-charcoal-200 font-mono pt-1 border-t border-white/10">
                  <span>${vid.duration_seconds || 55}s</span>
                  <span>${vid.file_size_mb || '0'} MB</span>
                </div>
              </div>
            </div>
          `)}
        </div>
      `}
    </div>
  `;
}
