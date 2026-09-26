/**
 * ui/src/components/ChannelModal.js
 * =================================
 * Channel profile creator and editor with live voice synthesis testing.
 * Redesigned with Charcoal & Electric Lime design system.
 */

import { html, useState } from '../html.js';
import { Icon } from './Icons.js';
import { api } from '../api/client.js';
import { usePipeline } from '../context/PipelineContext.js';

export function ChannelModal({ isOpen, onClose, channel = null }) {
  if (!isOpen) return null;

  const { refreshChannels, showToast } = usePipeline();
  const isEditing = Boolean(channel);

  const [name, setName] = useState(channel ? channel.name : "");
  const [displayName, setDisplayName] = useState(channel ? channel.display_name : "");
  const [niche, setNiche] = useState(channel ? channel.niche : "Artificial Intelligence & Future Technology");
  const [tone, setTone] = useState(channel ? channel.tone : "Fast-paced, suspenseful, mind-blowing");
  const [voiceName, setVoiceName] = useState(channel ? channel.voice_name : "en-US-ChristopherNeural");
  const [voiceRate, setVoiceRate] = useState(channel ? channel.voice_rate : "+8%");
  const [bgmMood, setBgmMood] = useState(channel ? channel.default_bgm_mood : "suspense");
  const [bgmVolume, setBgmVolume] = useState(channel ? channel.bgm_volume : 0.22);
  const [captionStyle, setCaptionStyle] = useState(channel ? channel.caption_style : "yellow_glow");

  const [testingVoice, setTestingVoice] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleTestVoice = async () => {
    setTestingVoice(true);
    try {
      const audioBlob = await api.channels.testVoice(voiceName, voiceRate, "Welcome to AIAutoShorts. Your autonomous video production engine is ready.");
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      audio.play();
    } catch (err) {
      showToast(`Voice preview failed: ${err.message}`, "error");
    } finally {
      setTestingVoice(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const payload = {
        name,
        display_name: displayName || name,
        niche,
        tone,
        voice_name: voiceName,
        voice_rate: voiceRate,
        default_bgm_mood: bgmMood,
        bgm_volume: parseFloat(bgmVolume),
        caption_style: captionStyle
      };

      if (isEditing) {
        await api.channels.update(channel.id, payload);
        showToast("Channel updated successfully!", "success");
      } else {
        await api.channels.create(payload);
        showToast("Channel created successfully!", "success");
      }
      await refreshChannels();
      onClose();
    } catch (err) {
      showToast(`Error saving channel: ${err.message}`, "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  return html`
    <div class="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-3 sm:p-4 overflow-y-auto">
      <div class="bg-charcoal-800 border border-charcoal-500 rounded-xl p-5 sm:p-6 max-w-xl w-full shadow-xl space-y-5 my-auto max-h-[92vh] overflow-y-auto">
        <div class="flex items-center justify-between border-b border-charcoal-500 pb-4">
          <div class="flex items-center space-x-2.5">
            <div class="p-2 rounded-lg bg-lime-primary/10 text-lime-primary border border-lime-primary/25">
              <${Icon} name="users" className="w-5 h-5" />
            </div>
            <div>
              <h3 class="text-base font-bold text-charcoal-100">
                ${isEditing ? `Edit Channel Profile: ${channel.display_name}` : 'Create Channel Profile'}
              </h3>
              <p class="text-xs text-charcoal-200">Target audience, tone, voice synthesis, and visual style</p>
            </div>
          </div>
          <button onClick=${onClose} class="text-charcoal-300 hover:text-charcoal-100 p-1 rounded-lg">
            <${Icon} name="close" className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit=${handleSubmit} class="space-y-4">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="space-y-1">
              <label class="text-xs font-semibold text-charcoal-200">Channel Slug (Identifier)</label>
              <input
                type="text"
                placeholder="tech_nexus"
                value=${name}
                onChange=${(e) => setName(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ''))}
                disabled=${isEditing}
                class="w-full bg-charcoal-700 border border-charcoal-500 text-xs rounded-lg p-2.5 text-charcoal-100 placeholder-charcoal-300 focus:outline-none focus:border-lime-primary focus:ring-1 focus:ring-lime-primary transition disabled:opacity-50"
                required
              />
            </div>
            <div class="space-y-1">
              <label class="text-xs font-semibold text-charcoal-200">Display Name</label>
              <input
                type="text"
                placeholder="Tech Nexus"
                value=${displayName}
                onChange=${(e) => setDisplayName(e.target.value)}
                class="w-full bg-charcoal-700 border border-charcoal-500 text-xs rounded-lg p-2.5 text-charcoal-100 placeholder-charcoal-300 focus:outline-none focus:border-lime-primary focus:ring-1 focus:ring-lime-primary transition"
                required
              />
            </div>
          </div>

          <div class="space-y-1">
            <label class="text-xs font-semibold text-charcoal-200">Niche & Core Subject</label>
            <input
              type="text"
              placeholder="e.g. Breakthrough AI robotics, quantum computing, and future science"
              value=${niche}
              onChange=${(e) => setNiche(e.target.value)}
              class="w-full bg-charcoal-700 border border-charcoal-500 text-xs rounded-lg p-2.5 text-charcoal-100 placeholder-charcoal-300 focus:outline-none focus:border-lime-primary focus:ring-1 focus:ring-lime-primary transition"
              required
            />
          </div>

          <div class="space-y-1">
            <label class="text-xs font-semibold text-charcoal-200">Channel Tone & Personality</label>
            <input
              type="text"
              placeholder="e.g. Suspenseful, high-velocity, mind-bending, authoritative"
              value=${tone}
              onChange=${(e) => setTone(e.target.value)}
              class="w-full bg-charcoal-700 border border-charcoal-500 text-xs rounded-lg p-2.5 text-charcoal-100 placeholder-charcoal-300 focus:outline-none focus:border-lime-primary focus:ring-1 focus:ring-lime-primary transition"
              required
            />
          </div>

          <!-- Neural Voice Settings -->
          <div class="p-4 rounded-xl bg-charcoal-700 border border-charcoal-500 space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold text-charcoal-100 flex items-center space-x-1.5">
                <${Icon} name="volume" className="w-4 h-4 text-lime-primary" />
                <span>Neural Voice Settings</span>
              </span>
              <button
                type="button"
                onClick=${handleTestVoice}
                disabled=${testingVoice}
                class="flex items-center space-x-1.5 px-3 py-1 rounded-lg bg-charcoal-600 hover:bg-charcoal-500 text-lime-primary text-xs font-semibold border border-charcoal-500 transition"
              >
                <${Icon} name=${testingVoice ? 'refresh' : 'play'} className="w-3.5 h-3.5 ${testingVoice ? 'animate-spin' : ''}" />
                <span>${testingVoice ? 'Synthesizing...' : 'Preview Voice'}</span>
              </button>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label class="text-[11px] text-charcoal-200 block mb-1">Voice Talent</label>
                <select
                  value=${voiceName}
                  onChange=${(e) => setVoiceName(e.target.value)}
                  class="w-full bg-charcoal-800 border border-charcoal-500 text-xs rounded-lg p-2 text-charcoal-100 focus:outline-none focus:border-lime-primary focus:ring-1 focus:ring-lime-primary"
                >
                  <option value="en-US-ChristopherNeural">Christopher (Deep, Narrative, Engaging)</option>
                  <option value="en-US-GuyNeural">Guy (Energetic, Youthful, Fast)</option>
                  <option value="en-US-JennyNeural">Jenny (Clear, Friendly, Modern)</option>
                  <option value="en-US-AriaNeural">Aria (Documentary, Crisp, Expressive)</option>
                  <option value="en-GB-RyanNeural">Ryan (British, Authoritative, Tech)</option>
                </select>
              </div>

              <div>
                <label class="text-[11px] text-charcoal-200 block mb-1">Pacing / Speed (${voiceRate})</label>
                <select
                  value=${voiceRate}
                  onChange=${(e) => setVoiceRate(e.target.value)}
                  class="w-full bg-charcoal-800 border border-charcoal-500 text-xs rounded-lg p-2 text-charcoal-100 focus:outline-none focus:border-lime-primary focus:ring-1 focus:ring-lime-primary"
                >
                  <option value="+0%">Normal (100%)</option>
                  <option value="+5%">Slightly Fast (+5%)</option>
                  <option value="+8%">Optimal Shorts Pacing (+8%)</option>
                  <option value="+12%">High Energy (+12%)</option>
                  <option value="+15%">Hyper Speed (+15%)</option>
                </select>
              </div>
            </div>
          </div>

          <!-- BGM & Caption Settings -->
          <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label class="text-xs font-semibold text-charcoal-200 block mb-1">Default BGM Mood</label>
              <select
                value=${bgmMood}
                onChange=${(e) => setBgmMood(e.target.value)}
                class="w-full bg-charcoal-700 border border-charcoal-500 text-xs rounded-lg p-2.5 text-charcoal-100 focus:outline-none focus:border-lime-primary focus:ring-1 focus:ring-lime-primary"
              >
                <option value="suspense">Suspense</option>
                <option value="dark">Dark & Cinematic</option>
                <option value="dramatic">Dramatic</option>
                <option value="upbeat">Upbeat & Inspiring</option>
                <option value="ambient">Ambient Sci-Fi</option>
                <option value="emotional">Emotional</option>
                <option value="trap">Heavy Trap</option>
              </select>
            </div>

            <div>
              <label class="text-xs font-semibold text-charcoal-200 block mb-1">
                BGM Volume (${Math.round(bgmVolume * 100)}%)
              </label>
              <input
                type="range"
                min="0.05"
                max="0.45"
                step="0.01"
                value=${bgmVolume}
                onChange=${(e) => setBgmVolume(e.target.value)}
                class="w-full mt-2 accent-lime-primary"
              />
            </div>

            <div>
              <label class="text-xs font-semibold text-charcoal-200 block mb-1">Caption Animation Style</label>
              <select
                value=${captionStyle}
                onChange=${(e) => setCaptionStyle(e.target.value)}
                class="w-full bg-charcoal-700 border border-charcoal-500 text-xs rounded-lg p-2.5 text-charcoal-100 focus:outline-none focus:border-lime-primary focus:ring-1 focus:ring-lime-primary"
              >
                <option value="yellow_glow">Yellow Glow (Karaoke)</option>
                <option value="hyper_neon">Hyper Neon (Green)</option>
                <option value="bold_red">Bold Red Accent</option>
                <option value="box_black">Black Bounding Box</option>
              </select>
            </div>
          </div>

          <!-- Action Buttons -->
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
              <span>${isSubmitting ? 'Saving...' : isEditing ? 'Update Channel' : 'Create Channel'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  `;
}
