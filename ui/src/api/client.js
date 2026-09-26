/**
 * ui/src/api/client.js
 * ====================
 * Robust authenticated REST API client for AIAutoShorts.
 */

const TOKEN_KEY = "aiautoshorts_access_token";

export const authStorage = {
  getToken: () => localStorage.getItem(TOKEN_KEY),
  setToken: (token) => localStorage.setItem(TOKEN_KEY, token),
  clearToken: () => localStorage.removeItem(TOKEN_KEY)
};

async function apiRequest(endpoint, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {})
  };

  const token = authStorage.getToken();
  if (token && !headers["Authorization"]) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const config = {
    ...options,
    headers
  };

  const response = await fetch(endpoint, config);

  if (response.status === 401) {
    // If not on login, could notify auth context
    authStorage.clearToken();
  }

  if (!response.ok) {
    let errorDetail = response.statusText;
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || JSON.stringify(errJson);
    } catch (_) {}
    throw new Error(errorDetail || `Request failed with status ${response.status}`);
  }

  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return await response.json();
  }
  return response;
}

export const api = {
  auth: {
    login: (username, password) => apiRequest("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password })
    }),
    register: (username, password, email) => apiRequest("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, password, email })
    }),
    getMe: () => apiRequest("/api/auth/me")
  },
  channels: {
    list: () => apiRequest("/api/channels"),
    create: (data) => apiRequest("/api/channels", {
      method: "POST",
      body: JSON.stringify(data)
    }),
    get: (id) => apiRequest(`/api/channels/${id}`),
    update: (id, data) => apiRequest(`/api/channels/${id}`, {
      method: "PUT",
      body: JSON.stringify(data)
    }),
    delete: (id) => apiRequest(`/api/channels/${id}`, {
      method: "DELETE"
    }),
    testVoice: async (voiceName, voiceRate, text) => {
      const resp = await fetch("/api/channels/test-voice", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ voice_name: voiceName, voice_rate: voiceRate, text })
      });
      if (!resp.ok) throw new Error("Voice preview failed");
      return await resp.blob();
    },
    getYouTubeAuthUrl: (id) => apiRequest(`/api/channels/${id}/youtube/auth-url`),
    disconnectYouTube: (id) => apiRequest(`/api/channels/${id}/youtube`, {
      method: "DELETE"
    })
  },
  pipeline: {
    listRuns: () => apiRequest("/api/pipeline/runs"),
    startRun: (data) => apiRequest("/api/pipeline/runs", {
      method: "POST",
      body: JSON.stringify(data)
    }),
    getRun: (id) => apiRequest(`/api/pipeline/runs/${id}`),
    cancelRun: (id) => apiRequest(`/api/pipeline/runs/${id}/cancel`, {
      method: "POST"
    }),
    approveHITL: (id, approved, feedback = "") => apiRequest(`/api/pipeline/runs/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ approved, feedback })
    }),
    cleanStaleRuns: () => apiRequest("/api/pipeline/runs/clean-stale", {
      method: "POST"
    })
  },
  media: {
    listVideos: () => apiRequest("/api/media/videos"),
    uploadToYouTube: (runId) => apiRequest(`/api/media/upload-youtube/${runId}`, {
      method: "POST"
    })
  },
  schedules: {
    list: () => apiRequest("/api/schedules"),
    create: (data) => apiRequest("/api/schedules", {
      method: "POST",
      body: JSON.stringify(data)
    }),
    update: (id, data) => apiRequest(`/api/schedules/${id}`, {
      method: "PUT",
      body: JSON.stringify(data)
    }),
    delete: (id) => apiRequest(`/api/schedules/${id}`, {
      method: "DELETE"
    }),
    trigger: (id) => apiRequest(`/api/schedules/${id}/trigger`, {
      method: "POST"
    })
  },
  analytics: {
    getOverview: () => apiRequest("/api/analytics/overview"),
    getExperiments: () => apiRequest("/api/analytics/experiments")
  },
  system: {
    getHealth: () => apiRequest("/api/system/health")
  },
  keys: {
    list: () => apiRequest("/api/keys"),
    add: (data) => apiRequest("/api/keys", {
      method: "POST",
      body: JSON.stringify(data)
    }),
    delete: (id) => apiRequest(`/api/keys/${id}`, {
      method: "DELETE"
    }),
    validate: (data) => apiRequest("/api/keys/validate", {
      method: "POST",
      body: JSON.stringify(data)
    })
  }
};
